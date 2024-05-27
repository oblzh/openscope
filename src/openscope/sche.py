import subprocess
import sys
import time
import os


# CMD0 = "./src/openscope/miner/signal_trade.py -config_file=./env/config.ini"
# CMD1 = "./src/openscope/miner/IQ50.py -config_file=./env/config.ini"
CMD0 = "src/openscope/miner/signal_trade.py"
CMD1 = "src/openscope/miner/IQ50.py"
# CMD0 = "src/openscope/miner/test.py"
USERNAME = os.getlogin()

def main():
    while True:
        procs = []
        for cmd in [CMD0, CMD1]:
            script = [f"/Users/{USERNAME}/.pyenv/shims/python", cmd, "-config_file=env/config.ini"]
            # script = [f"/Users/{USERNAME}/.pyenv/shims/python", cmd]
            proc = subprocess.Popen(script, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            procs.append(proc)
        while procs:
            for proc in procs:
                result = proc.poll()
                if result is not None: # 如果result为None，说明子进程还在运行
                    procs.remove(proc)
                    if result != 0: # 如果返回值非0，说明子进程运行出错
                        print(f'Script {proc.args[1]} terminated with error. Restarting all scripts.')
                        output, error = proc.communicate()
                        print(f"Output: {output}")
                        print(f"Error: {error}")
                        for p in procs:
                            p.terminate()
                        break
                else:
                    continue
        time.sleep(300)
        procs = []


if __name__ == '__main__':
    main()
