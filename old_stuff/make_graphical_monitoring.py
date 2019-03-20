import sys,os
IPYNB_FILENAME = 'Monitoring.ipynb'
CONFIG_FILENAME = '.config_ipynb'

def main(argv):
        with open(CONFIG_FILENAME,'w') as f:
                f.write(' '.join(argv))
        os.system('jupyter nbconvert --execute {:s} --to html'.format(IPYNB_FILENAME))
        return None

if __name__ == '__main__':
        main(sys.argv)
