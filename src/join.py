import configparser
from peer import Peer
from threading import Thread
# import Pyro4.naming
import Pyro5
import re
import socket
import random
import sys
import time

def get_people(config):
    # if len(sys.argv) == 3:
        # if there is a second command line input, let that be the number of peers spawned
        # n_people = int(sys.argv[2])
    # else:
    #     # otherwise, default to the number specified in the config file
    #     n_people = int(config["DEFAULT"]["N_PEOPLE"])
    n_people = 6
    n_items = 5
    max_neighbors = 1
    roles = ['buyer', 'seller']
    goods = ['fish', 'salt', 'boar']
    ns_name = sys.argv[1]
    people = []
    hopcount = 3
    # hmac_key = config["NETWORK_INFO"]["HMAC_KEY"]

    # Starts name server
    try:
        # ns = Pyro4.locateNS(host = ns_name)
        ns = Pyro5.api.locate_ns()
    except Exception:
        print("No server found, start one")
        # Thread(target=Pyro4.naming.startNSloop, kwargs={"host": ns_name, "hmac": hmac_key}).start()
        # Thread(target=Pyro4.naming.startNSloop, kwargs={"host": ns_name}).start()
        Thread(target=Pyro5.nameserver.start_ns_loop, kwargs={"host": ns_name}).start()
        time.sleep(2)
        # haskey = True

    # Future implementation may include hmac key for security
    # haskey = False

    # # at least 1 buyer
    # role = 'buyer'
    # id = role + str(n_people-2)
    # people.append(Peer(id, role, n_items, goods, ns_name))

    # at least 1 seller
    role = 'seller'
    id = role + str(n_people-1)
    people.append(Peer(id, role, n_items, goods, ns_name, max_neighbors, hopcount))

    for i in range(n_people - 5):
        role = roles[0] # roles[random.randint(0,len(roles) - 1)]
        id = role + str(i) # + socket.gethostname()
        # n_items = int(config["DEFAULT"]["N_ITENS"])
        peer = Peer(id, role, n_items, goods, ns_name, max_neighbors, hopcount)
        people.append(peer)

    return people


if __name__ == "__main__":

    # config = configparser.ConfigParser()
    # config.read("config")

    # people = get_people(config)
    people = get_people(None)

    time.sleep(2)
    try:
        for person in people:
            person.start()
    except KeyboardInterrupt:
        sys.exit()






