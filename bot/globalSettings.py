import argparse
import configparser

config = None


def init():
    global config

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", 
            dest="configFile",
            help="Relative Path to config file",
            required=True)
    args = parser.parse_args()

    config = configparser.ConfigParser(delimiters=('='))
    config.read(args.configFile)
