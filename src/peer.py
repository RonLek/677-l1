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
        """
        Construct a new 'Peer' object.

        :param id: The id of the peer
        :param role: The role of the peer
        :param product_count: The maximum number of products the peer can sell (if role is seller)
        :param products: The list of products that a peer can buy or sell
        :param hostname: The hostname of the peer
        :return: returns nothing
        """

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
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.seller_list_lock = Lock()
        self.product_count_lock = Lock()
        self.seller_list = []

    def get_random_neighbors(self):
        """
        Create a neighbor list and assign neighbors to the peer
        :return: returns nothing
        """
        neighbor_list = []
        ns_dict = self.ns.list()
        re_pattern = "seller[0-9]+|buyer[0-9]+"
        for id in ns_dict:
            if "NameServer" not in id and self.id != id and re.match(re_pattern, id):
                neighbor_list.append(id)
        self.connect_neighbors(neighbor_list)

        neighbor_list.clear()

        # TODO: add neighbors with different hostname

    def connect_neighbors(self, neighbor_list):
        """
        Select at most 3 random neighbors from the neighbor list and connect to them
        :param neighbor_list: The list of neighbors
        :return: nothing
        """
        if neighbor_list:
            for i in range(3):
                if self.get_neighbor_len() >= 3:
                    break
                random_neighbor_id = neighbor_list[random.randint(0, len(neighbor_list)-1)]
                self.neighbors[random_neighbor_id] = self.ns.lookup(random_neighbor_id)

                with Pyro5.api.Proxy(self.neighbors[random_neighbor_id]) as neighbor:
                    try:
                        self.executor.submit(neighbor.add_neighbor, self.id)
                    except Exception as e:
                        print(datetime.datetime.now(), "Exception in connect_neighbors", e)

    @Pyro5.server.expose
    def add_neighbor(self, neighbor_id):
        """
        Add a neighbor to the peer's neighbor list
        :param neighbor_id: The id of the neighbor to add
        :return: nothing
        """
        if neighbor_id not in self.neighbors.keys():
            self.neighbors[neighbor_id] = self.ns.lookup(neighbor_id)

    @Pyro5.server.expose
    def get_neighbor_len(self):
        """
        Get the number of neighbors of the peer
        :return: The number of neighbors
        """
        return len(self.neighbors.keys())

    def get_nameserver(self, ns_name):
        """
        Get the nameserver proxy
        :param ns_name: The hostname of the nameserver
        :return: The nameserver proxy
        """

        try:
            ns = Pyro5.core.locate_ns(host=ns_name)
            return ns
        except Exception as e:
            template = "An exception of type {0} occurred at get_nameserver. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print(message)

    def run(self):
        """
        Starts the market simulation
        :return: nothing
        """

        try:
            with Pyro5.server.Daemon(host=self.hostname) as daemon:
                uri = daemon.register(self)
                # claim thread ownership of ns server proxy
                self.ns._pyroClaimOwnership()
                self.ns.register(self.id, uri)
                if self.role == "buyer":
                    print(datetime.datetime.now(), self.id, "joins to buy ", self.product_name)
                else:
                    print(datetime.datetime.now(), self.id, "joins to sell ", self.product_name)

                self.executor.submit(daemon.requestLoop)
                time.sleep(1)

                self.get_random_neighbors()

                while True and self.role == "buyer":

                    for neighbor_name in self.neighbors:
                        with Pyro5.api.Proxy(self.neighbors[neighbor_name]) as neighbor:
                            search_path = [self.id]
                            print(datetime.datetime.now() , self.id, "searching for ", self.product_name, " in ", neighbor_name)
                            neighbor.lookup(self.id, self.product_name, 10, search_path)

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
        """
        Lookup a product in the peer's neighbor list
        :param bID: The id of the buyer
        :param product_name: The name of the product to lookup
        :param hopcount: The number of hops left
        :param search_path: The path of the search
        :return: nothing
        """
        # this procedure, executed initially by buyer processes then recursively 
        # between directly connected peer processes in the network, should search 
        # the network; all matching sellers respond to this message with their IDs. 
        # The hopcount, which should be set lower than the maximum distance between peers in the network, 
        # is decremented at each hop and the message is discarded when it reaches 0.
        
        last_peer = search_path[-1]
        hopcount -= 1

        if hopcount < 0:
            return

        try:
            if self.role == "seller" and self.product_name == product_name and self.product_count >= 0:
                print(datetime.datetime.now(), "seller found with ID: ", self.id)
                # inserting seller id at the front of the search path for easier reply
                search_path.insert(0, self.id)
                self.executor.submit(self.reply, self.id, search_path)

            else:
                # continue lookup
                for neighbor_name in self.neighbors:
                    if neighbor_name != last_peer:
                        with Pyro5.api.Proxy(self.neighbors[neighbor_name]) as neighbor:
                            if self.id not in search_path:
                                search_path.append(self.id)
                            self.executor.submit(neighbor.lookup, bID, product_name, hopcount, search_path)

        except Exception as e:
            print(datetime.datetime.now(), "Exception in lookup", e)
            return

    @Pyro5.server.expose
    def buy(self, peer_id):
        """
        Buy a product from the seller
        :param peer_id: The id of the buyer
        :return: nothing
        """

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
        """
        Build the seller list for the buyer
        :param peer_id: The id of the seller
        :param reply_path: The complete path of the reply
        :return: nothing
        """

        try:
            # only 1 peer id in reply_path which is the seller
            if reply_path and len(reply_path) == 1:
                print(datetime.datetime.now(), "Seller", peer_id, "responded to buyer", self.id)

                # adding seller to the list of sellers
                with self.seller_list_lock:
                    if reply_path[0] not in self.seller_list:
                        self.seller_list.extend(reply_path)

            elif reply_path and len(reply_path) > 1:
                intermediate_peer = reply_path.pop()
                with Pyro5.api.Proxy("PYRONAME:" + intermediate_peer) as neighbor:
                    neighbor.reply(peer_id, reply_path)

        except Exception as e:
            template = "An exception of type {0} occurred at Reply. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print(datetime.datetime.now(), message)
            sys.exit()
