# -*- coding: utf-8 -*-
# @Time     :2023/12/26 17:00
# @Author   :ym
# @File     :main.py
# @Software :PyCharm
import asyncio
import random
import ssl
import json
import sys
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect


async def connect_to_wss(socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(device_id)
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4650/"
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(20)

                # asyncio.create_task(send_http_request_every_10_seconds(socks5_proxy, device_id))
                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    logger.info(socks5_proxy)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "2.5.0"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            logger.error(e)
            logger.error(socks5_proxy)


async def main():
    config = type('config', (object,), {'proxies': [], 'user_id': ''})()
    config_path = (len(sys.argv) > 1 and sys.argv[1]) or 'config.json'
    try:
        with open(config_path, 'r') as f:
            config_file = json.load(f)
            config.user_id = config_file['user_id']
            for c in config_file['proxies']:
                config.proxies.append(c)
    except FileNotFoundError:
        logger.error('config file is not exist')
        return
    if len(config.proxies) == 0:
        logger.error('proxies is empty')
        return
    print("config", config.proxies, config.user_id)
    tasks = [asyncio.ensure_future(connect_to_wss(i, config.user_id)) for i in config.proxies]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
