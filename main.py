import requests
import time
import random
import logging
from itertools import cycle
from web3 import Web3

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# RPC-сервер Monad
MONAD_RPC = "https://testnet-rpc.monad.xyz"

def load_file(file_path):
    """Загружает данные из файла (кошельки или прокси)."""
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except Exception as e:
        logging.error(f"Ошибка при загрузке {file_path}: {e}")
        return []

def get_monad_balance(address, w3):
    """Получает баланс MONAD кошелька."""
    try:
        checksum_address = Web3.to_checksum_address(address)
        balance_wei = w3.eth.get_balance(checksum_address)
        balance_ether = w3.from_wei(balance_wei, "ether")
        return float(balance_ether)
    except Exception as e:
        logging.error(f"Ошибка при получении баланса Monad для {address}: {e}")
        return 0.0

def get_xp_balance(address, proxy):
    """Получает XP через Zerion API с использованием прокси."""
    url = f"https://zpi.zerion.io/wallet/get-meta/v1?identifiers={address}"
    headers = {
        "Zerion-Client-Type": "web",
        "Zerion-Client-Version": "1.143.1"
    }
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }

    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()
        json_data = response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса {address} через {proxy}: {e}")
        return 0

    # Получаем XP из ответа
    membership = json_data.get("data", [{}])[0].get("membership", {})
    retro = membership.get("retro", {})

    # Проверяем, есть ли retro (иначе ставим 0)
    if not isinstance(retro, dict):
        return 0

    zerion_total = retro.get("zerion", {}).get("total", 0)
    global_total = retro.get("global", {}).get("total", 0)
    return zerion_total + global_total

def main():
    wallets_file = "wallets.txt"
    proxy_file = "proxy.txt"
    output_file = "result.txt"

    # Загружаем кошельки и прокси
    wallets = load_file(wallets_file)
    proxies = load_file(proxy_file)

    if not wallets:
        logging.error("Нет кошельков для проверки.")
        return
    if not proxies:
        logging.error("Нет доступных прокси!")
        return

    proxy_cycle = cycle(proxies)  # Цикл прокси
    w3 = Web3(Web3.HTTPProvider(MONAD_RPC))  # Подключение к Monad

    if not w3.is_connected():
        logging.error("Не удалось подключиться к Monad RPC")
        return

    results = []
    for i, wallet in enumerate(wallets, 1):
        proxy = next(proxy_cycle)  # Берем прокси по порядку

        xp_balance = get_xp_balance(wallet, proxy)
        monad_balance = get_monad_balance(wallet, w3)

        result_line = f"{wallet} - {xp_balance} XP \\ {monad_balance:.5f} MONAD"
        results.append(result_line)

        logging.info(f"Проверен {i}/{len(wallets)} через {proxy}: {result_line}")
        time.sleep(random.uniform(0.5, 1))  # Задержка между запросами

    # Сохранение результатов
    with open(output_file, "w") as outfile:
        outfile.write("\n".join(results))

    logging.info(f"Результаты сохранены в {output_file}")

if __name__ == "__main__":
    main()
