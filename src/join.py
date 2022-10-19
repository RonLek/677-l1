from peer import Peer
from threading import Thread
import Pyro5
import re
import socket
import random
import sys
import time

def get_people(config):
    n_people = 2
    n_items = 5
    roles = ['buyer', 'seller']
    goods = ['fish', 'salt', 'boar']
    ns_name = sys.argv[1]
    people = []
    # hmac_key = config["NETWORK_INFO"]["HMAC_KEY"]

    # Starts name server
    try:
        ns = Pyro5.api.locate_ns()
    except Exception:
        print("No server found, start one")
        Thread(target=Pyro5.nameserver.start_ns_loop, kwargs={"host": ns_name}).start()
        time.sleep(2)

    # at least 1 buyer
    role = 'buyer'
    id = role + str(n_people-2)
    people.append(Peer(id, role, n_items, goods, ns_name))

    # at least 1 seller
    role = 'seller'
    id = role + str(n_people-1)
    people.append(Peer(id, role, n_items, goods, ns_name))

    for i in range(n_people - 2):
        role = roles[random.randint(0,len(roles) - 1)]
        id = role + str(i) # + socket.gethostname()
        peer = Peer(id, role, n_items, goods, ns_name)
        people.append(peer)

    return people


if __name__ == "__main__":

    people = get_people(None)

    time.sleep(2)
    try:
        for person in people:
            person.start()
    except KeyboardInterrupt:
        sys.exit()






