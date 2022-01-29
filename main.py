from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import bot.tacobot as bot

def main():
    tacobot = bot.TacoBot()

if __name__ == '__main__':
    main()
