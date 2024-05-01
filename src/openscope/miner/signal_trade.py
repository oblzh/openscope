#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/26 18:04
# @Author  : long.zhang
# @Contact : long.zhang@opg.global
# @Site    : scope
# @File    : signal_trade.py
# @Software: PyCharm
# @Desc    :
# @Cmd     :
import argparse
import json
import os
import sys
import time
from abc import ABC
from os.path import dirname, realpath
from urllib.parse import urlparse

import requests
import uvicorn
from communex.compat.key import classic_load_key
from communex.module.module import Module, endpoint  # type: ignore
from communex.module.server import ModuleServer  # type: ignore
from fastapi import HTTPException
from keylimiter import TokenBucketLimiter

sys.path.append(f'{dirname(dirname(dirname(dirname(realpath(__file__)))))}')
from config import Config
from src.openscope.key import sign_message
from src.openscope.utils import is_ethereum_address, log


class TradeModule(ABC, Module):
    trade_url = 'http://47.236.87.93:8000/createtrade'

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def _validate_required_params(data: dict, required_params: list[str]) -> None:
        missing_params = [param for param in required_params if param not in data]
        if missing_params:
            raise HTTPException(status_code=400, detail=f"Missing required parameters: {missing_params}")

    @endpoint
    def trade(self, data: dict):
        try:
            log(f'data: {data}')
            self._validate_required_params(data, ['token', 'position_manager', 'direction'])
            miner_id = os.getenv('SIGNAL_TRADE_ADDRESS')
            pub_key = os.getenv('SIGNAL_TRADE_PUBLIC_KEY')
            nonce = int(time.time() * 1000)
            token = data['token'].lower()
            if not is_ethereum_address(token):
                raise HTTPException(status_code=400, detail=f"The token: {token} is an invalid EVM address")
            position_manager = data['position_manager']
            direction = int(data['direction'])
            timestamp = nonce // 1000

            trade_data = {'miner_id': miner_id, 'pub_key': pub_key, 'nonce': nonce, 'token': token,
                          'position_manager': position_manager, 'direction': direction, 'timestamp': timestamp}
            sing_msg = f'{miner_id}{pub_key}{nonce}{token}{position_manager}{direction}{timestamp}'
            signature = sign_message(os.getenv('SIGNAL_TRADE_PRIVATE_KEY'), sing_msg)
            trade_data['signature'] = signature
            log(f'trade_data: {trade_data}')
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.post(
                url=self.trade_url,
                headers=headers,
                data=json.dumps(trade_data)
            )
            log(response.text)
            response.raise_for_status()
            if response.json().get('code') != 200:
                raise HTTPException(status_code=response.json().get('code'), detail=response.json().get('msg'))
        except Exception as e:
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e  # type: ignore


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="subscription event")
    parser.add_argument("-config_file", type=str,
                        default=os.path.join(f'{dirname(dirname(dirname(dirname(realpath(__file__)))))}',
                                             'env/config.ini'), help=f"config file path")
    args = parser.parse_args()
    config_file = args.config_file
    config = Config(config_file=config_file)
    keypair = classic_load_key(config.miner.get("keyfile"))
    url = config.miner.get("url")
    parsed_url = urlparse(url)
    log(f"Running module with key {keypair.ss58_address}")
    os.environ["SIGNAL_TRADE_ADDRESS"] = keypair.ss58_address
    os.environ["SIGNAL_TRADE_PUBLIC_KEY"] = keypair.public_key.hex()
    os.environ["SIGNAL_TRADE_PRIVATE_KEY"] = keypair.private_key.hex()
    claude = TradeModule()
    refill_rate = 1 / 400
    bucket = TokenBucketLimiter(10, refill_rate)
    server = ModuleServer(
        claude, keypair, ip_limiter=bucket, subnets_whitelist=[3]
    )
    app = server.get_fastapi_app()
    app.add_api_route("/trade", claude.trade, methods=["POST"])
    uvicorn.run(app, host=parsed_url.hostname, port=parsed_url.port)