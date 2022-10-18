# class to implement a peer - can be a buyer or a seller
import Pyro5.server
import Pyro5.api
from concurrent.futures import ThreadPoolExecutor
from threading import Thread, Lock
import datetime
import time
import random
import re
import sys

class Peer(Thread):

    def __init__(self, id, role, product_count, products, hostname):
        Thread.__init__(self)
        self.id = id
        self.hostname = hostname
        self.neighbors = {}
        self.role = role
        self.products = products
        self.product_name = self.products[random.randint(0, len(self.products)-1)]
        self.n = product_count
        self.product_count = product_count
        self.role = role
        self.ns = self.get_nameserver(hostname)
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.seller_list_lock = Lock()
        self.product_count_lock = Lock()
        self.seller_list = []

    def get_random_neighbors(self):
        neighbor_list = []
        ns_dict = self.ns.list()
        re_pattern = "seller[0-9]+|buyer[0-9]+"
        # print("ns_dict", ns_dict)
        for id in ns_dict:
            if "NameServer" not in id and self.id != id and re.match(re_pattern, id):
                neighbor_list.append(id)
        self.connect_neighbors(neighbor_list)

        neighbor_list.clear()

        # TODO: add neighbors with different hostname

    def connect_neighbors(self, neighbor_list):

        # randomly pick one neighbor
        # print("neighbor list", neighbor_list)
        if neighbor_list:
            for i in range(3):
                random_neighbor_id = neighbor_list[random.randint(0, len(neighbor_list)-1)]
                self.neighbors[random_neighbor_id] = self.ns.lookup(random_neighbor_id)

            with Pyro5.api.Proxy(self.neighbors[random_neighbor_id]) as neighbor:
                try:
                    self.executor.submit(neighbor.add_neighbor, self.id)
                except Exception as e:
                    print(datetime.datetime.now(), "Exception in connect_neighbors", e)

    @Pyro5.server.expose
    def add_neighbor(self, neighbor_id):
        if neighbor_id not in self.neighbors:
            self.neighbors[neighbor_id] = self.ns.lookup(neighbor_id)

    def get_nameserver(self, ns_name):

        try:
            ns = Pyro5.core.locate_ns(host=ns_name)
            return ns
        except Exception as e:
            template = "An exception of type {0} occurred at get_nameserver. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print(message)

    def run(self):

        try:
            with Pyro5.server.Daemon(host=self.hostname) as daemon:
                uri = daemon.register(self)
                # claim thread ownership of ns server proxy
                self.ns._pyroClaimOwnership()
                self.ns.register(self.id, uri)
                if self.role == "buyer":
                    print(datetime.datetime.now(), self.id, "joins to buy ", self.product_name)
                    time.sleep(1)
                else:
                    print(datetime.datetime.now(), self.id, "joins to sell ", self.product_name)
                    time.sleep(1)

                self.executor.submit(daemon.requestLoop)
                self.get_random_neighbors()

                while True and self.role == "buyer":

                    # lookup_requests = []

                    # print(self.neighbors, "\n")
                    for neighbor_name in self.neighbors:
                        with Pyro5.api.Proxy(self.neighbors[neighbor_name]) as neighbor:
                            search_path = [self.id]
                            print(datetime.datetime.now() , self.id, "searching for ", self.product_name, " in ", neighbor_name)
                            # print("neighbor", neighbor)
                            # neighbor._pyroClaimOwnership()
                            neighbor.lookup(self.id, self.product_name, 5, search_path)
                            # print("lookup_requests", lookup_requests)

                    # for request in lookup_requests:

                    #     request.result()

                    with self.seller_list_lock:

                        print(datetime.datetime.now(), "seller list for ", self.id , "is: ", self.seller_list)
                        # select random seller
                        if self.seller_list:
                            random_seller = self.seller_list[random.randint(0, len(self.seller_list)-1)]

                            with Pyro5.client.Proxy(self.neighbors[random_seller]) as seller:
                                seller._pyroClaimOwnership()
                                seller.buy(self.id)
                        else:
                            print(datetime.datetime.now(), "no sellers found within hop limit for ", self.id)
                        
                        self.seller_list = []
                        self.product_name = self.products[random.randint(0, len(self.products)-1)]

                    time.sleep(1)

                # Seller loop
                while True:
                    time.sleep(1)

        except Exception as e:
            print("Exception in main", e)
                            

    @Pyro5.server.expose
    def lookup(self, bID, product_name, hopcount, search_path):
        # this procedure, executed initially by buyer processes then recursively 
        # between directly connected peer processes in the network, should search 
        # the network; all matching sellers respond to this message with their IDs. 
        # The hopcount, which should be set lower than the maximum distance between peers in the network, 
        # is decremented at each hop and the message is discarded when it reaches 0.
        
        last_peer = search_path[-1]
        # print(self.id, "\nneighbors")
        # print(self.neighbors)        
        hopcount -= 1

        if hopcount < 0:
            return

        try:
            if self.role == "seller" and self.product_name == product_name and self.product_count > 0:
                print(datetime.datetime.now(), "seller found with ID: ", self.id)
                # inserting seller id at the front of the search path for easier reply
                search_path.insert(0, self.id)
                self.executor.submit(self.reply, self.id, search_path)

            else:
                # continue lookup
                # print("within continue lookup")
                for neighbor_name in self.neighbors:
                    if neighbor_name != last_peer:
                        with Pyro5.api.Proxy(self.neighbors[neighbor_name]) as neighbor:
                            # print("neighbor within continue lookup", neighbor)
                            if self.id not in search_path:
                                search_path.append(self.id)
                            self.executor.submit(neighbor.lookup, bID, product_name, hopcount, search_path)

        except Exception as e:
            print(datetime.datetime.now(), "Exception in lookup", e)
            return

    @Pyro5.server.expose
    # :peer_id: the id of the buyer
    def buy(self, peer_id):

        try:
            with self.product_count_lock:
                if self.product_count > 0:

                    self.product_count -= 1
                    print("*******\n", datetime.datetime.now(), peer_id, "bought", self.product_name, "from", self.id, self.product_count, "remain now", "\n*******")
                    return True
            
                # if self.product_count == 0, pick random item to sell
                else:
                    print(datetime.datetime.now(), peer_id, "failed to buy", self.product_name, "from", self.id, "no more items")
                    self.product_name = self.products[random.randint(0, len(self.products) - 1)]
                    self.product_count = self.n
                    print(datetime.datetime.now(), self.id , "now selling", self.product_name)
                    return False
        except Exception as e:
            print(datetime.datetime.now(), "Exception in buy", e)
            return

    @Pyro5.server.expose
    def reply(self, peer_id, reply_path):

        # print("reply_path", reply_path)
        try:
            # only 1 peer id in reply_path which is the seller
            if reply_path and len(reply_path) == 1:
                print(datetime.datetime.now(), "Seller", peer_id, "responded to buyer", self.id)

                # adding seller to the list of sellers
                with self.seller_list_lock:
                    self.seller_list.extend(reply_path)

            elif reply_path and len(reply_path) > 1:
                intermediate_peer = reply_path.pop()
                # print("self.neighbors", self.neighbors)
                # print("intermediate_peer", intermediate_peer)
                with Pyro5.api.Proxy("PYRONAME:" + intermediate_peer) as neighbor:
                    neighbor.reply(peer_id, reply_path)

        except Exception as e:
            template = "An exception of type {0} occurred at Reply. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print(datetime.datetime.now(), message)
            sys.exit()

