# Import graphviz
import sys, os, copy
from music21 import pitch, duration
sys.path.append('..')
sys.path.append('/usr/lib/graphviz/python/')
sys.path.append('/usr/lib64/graphviz/python/')
import graphviz

from graphviz import Digraph

class GraphError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return repr(self.message)


# class to mark init variables as such ...
class Gvar():
    def __init__(self, key):
        self.key = key
    def __repr__(self):
        return "?" + str(self.key)
    
# function for runtime evaluation ... see graa_function_evaluator for function evaluation
class Func():
    def __init__(self, name, func_args, func_kwargs):
        self.name = name
        self.args = func_args
        self.kwargs = func_kwargs
    # string to ensure output
    def __repr__(self):
        func_string = self.name + "<"
        for arg in self.args:
            func_string += str(arg) + ":"        
        for key in self.kwargs:
            func_string += str(key) + "=" + str(self.kwargs[key]) + ":"
        func_string = func_string[:-1]
        func_string += ">"
        return func_string


# some mappings to get a music21 note to a graa note
duration_mapping = { "q":1.0, "h":2.0,"w":4.0,"e":0.5, "st":0.25, "ts":0.125, "sf":0.0625 }
dot_mapping = { "d":1, "dd":2 }
acc_mapping = { "is":"#", "es":"-", "isis": "##", "eses":"--" }
inv_duration_mapping = { "quarter":"q", "half":"h","whole":"w","eight":"e", "16th":"st", "32th":"ts", "64th":"sf" }
inv_dot_mapping = {v: k for k, v in dot_mapping.items()}

# define note class to get representation right
class GraaNote():    
    def __init__(self, pitch_string):
        self.pitch = pitch.Pitch(pitch_string)
        self.absolute_duration = None
        self.vel = None        
    def __repr__(self):        
        note_string = self.pitch.nameWithOctave.lower()
        note_string = note_string.replace("#", "is")
        note_string = note_string.replace("-", "es")        
        return note_string
    def __add__(self, other):
        other = int(other)
        self.pitch.midi = self.pitch.midi + other
        return self
    def __sub__(self, other):
        other = int(other)
        self.pitch.midi = self.pitch.midi - other
        return self
    def __hash__(self):
        return str(self).__hash__()
    def __lt__(self, other):
        if type(other) is int:
            return self.pitch.midi < other
        else:
            return self.pitch.midi < other.pitch.midi
    def __le__(self, other):
        if type(other) is int:
            return self.pitch.midi <= other
        else:
            return self.pitch.midi <= other.pitch.midi
    def __ge__(self, other):
        #print(type(self), type(other))
        #print("SELF " + str(self) + " OTHER " +  str(other))
        if type(other) is int:
            return self.pitch.midi >= other
        else:
            return self.pitch.midi >= other.pitch.midi
    def __eq__(self, other):
        if type(other) is int:
            return self.pitch.midi == other
        else:
            return self.pitch.midi == other.pitch.midi
      
"""
A node, consisting of an id, content and some meta information 

"""
class Node():
    def __init__(self, graph_id, node_id, node_content, meta=""):        
        # graph id basically only needed for pretty printing
        self.graph_id = graph_id
        self.id = node_id
        self.content = node_content
        # space for arbitrary meta information
        self.meta = meta
        self.mute = False
    def __repr__(self):
        node_string="{}{}|".format(self.graph_id, self.id)
        # have to decide between normal and overlay nodes here ... 
        if type(self.content) is Func:
            # a normal node contains just one function
            node_string += self.content.name
            node_string += "~"
            for arg in self.content.args:
                node_string += str(arg) + ":"
            for key in self.content.kwargs:
                node_string += str(key) + "=" + str(self.content.kwargs[key]) + ":"
            # remove last ':'
            node_string = node_string[:-1] 
        else:
            # this should mean it's an ol node, as it contains a dict of functions
            if type(self.content) is str:
                node_string += self.content
            else:
                for key in self.content:
                    node_string += str(key) + "=" + str(self.content[key]) + ":"
            # remove last ':'
            node_string = node_string[:-1] 
        return node_string

"""
An edge, consisting of the destination node, the transition probability and the transition duration.

If transition probability is None, it will be calculated when the edge is added.

"""
class Edge():
    def __init__(self, graph_id, source, destination_node_id, transition_duration, transition_probability=None, meta=""):
        # source and graph id basically only needed for pretty printing
        self.source = source
        self.graph_id = graph_id
        self.dest = destination_node_id
        self.prob = transition_probability
        # might also contain function to modify duration
        self.dur = transition_duration
        # some meta information, like steps or so ... 
        self.meta = meta
    def __repr__(self):
        source_string = "{}{}".format(self.graph_id, self.source)
        dest_string = "->{}{}".format(self.graph_id, self.dest)
        trans_string = ""
        if self.dur is not None:
            trans_string += "-"
            if type(self.dur) is list:
                trans_string += self.dur[0] + "("
                for arg in self.dur[1]:
                    trans_string += str(arg) + ","
                trans_string = trans_string[:-1] + ")"
            else:
                trans_string += str(self.dur)
        if self.prob is not None:
            trans_string += ":"            
            if type(self.prob) is list:                
                trans_string += self.prob[0] + "("
                for arg in self.prob[1]:
                    trans_string += str(arg) + ","
                trans_string = trans_string[:-1] + ")"
            else:
                trans_string += str(self.prob)
        return source_string + trans_string + dest_string


"""
The main graph class!
"""
class Graph():
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.start_node_id = None
        self.current_node_id = None
        self.steps = 0
    def __str__(self):
        graph_string = ""
        sorted_nodes = list(self.nodes.keys())
        sorted_nodes.sort()
        for node in sorted_nodes:
            graph_string += str(self.nodes[node]) + ",\n"
        for node in sorted_nodes:
            for edge in self.edges[node]:
                graph_string += str(edge) + ",\n"
        # remove last comma
        return graph_string[:-2] + "\n"
    def add_node(self, node):
        # by convention, first added node is start node
        if self.start_node_id == None:
            self.start_node_id = node.id
            self.current_node_id = node.id
        # only intialize edges if node not present yet
        if node.id not in self.nodes.keys():    
            self.edges[node.id] = []
        self.nodes[node.id] = node
    # Add an edge, a tuple of destination node and transition
    def add_edge(self, source_node_id, new_edge):
        if source_node_id not in self.nodes or new_edge.dest not in self.nodes:
            raise GraphError("nodes for this edge not present")
        else:
            #check if there's already an edge in that respective direction, and remove it
            for edge in self.edges[source_node_id]:
                if edge.dest == new_edge.dest:
                    self.edges[source_node_id].remove(edge)
            if new_edge.prob == None:
                new_prob = int(100/(len(self.edges[source_node_id]) + 1))
                for edge in self.edges[source_node_id]:
                    edge.prob = new_prob
                new_edge.prob = new_prob
            self.edges[source_node_id].append(new_edge)
    def render(self, filename, render="content"):
        dot = Digraph(comment="",edge_attr={'len': '6', 'weight':'0.00001'})
        dot.engine = 'dot'
        # add nodes to dot graph
        for node_key in self.nodes.keys():
            node_content = "nil"
            # either use id or content to mark graph nodes
            if render == "id":
                node_content = str(self.nodes[node_key].id)
            elif render == "content":
                node_content = str(self.nodes[node_key].content)
            else:
                node_content = str(self.nodes[node_key].id) + ":" + str(self.nodes[node_key].content)
            dot.node(str(self.nodes[node_key].id), node_content)
        #add edges to dot graph
        for edge_key in self.edges.keys():
            for edge in self.edges[edge_key]:
                dot.edge(str(edge_key), str(edge.dest), label="{}ms:{}%".format(edge.dur, edge.prob))
        if not os.path.exists("graph"):
            os.makedirs("graph")
        dot.render("graph/" + filename + ".gv")

class GraphTool():
    # destructively reverse direction of edges 
    def reverse_digraph(self, graph):
        for i in range(0, len(graph.nodes)):
            node = graph.nodes[i]
            for edge in graph.edges[node.id]:
                # don't touch self-referential edges ...
                if edge.dest != node.id:
                    rev_edge = Edge(node.id, edge.dur, edge.prob) 
                    graph.add_edge(edge.dest, rev_edge)
                    graph.edges[node.id].remove(edge)
                    
    
class TraversalTool():
    # returns node traversal, breadth first
    def bf_trav(self, graph):
        node_stack = []
        nodes_unvisited = [x for x in range(0,len(graph.nodes) + 1)]
        traversal_list = []
        #remove start node and push to stack
        nodes_unvisited.remove(0)
        node_stack.append(0)
        traversal_list.append(0)
        while len(node_stack) != 0:
            current_node = node_stack.pop()
            for edge in graph.edges[current_node]:
                if edge.dest in nodes_unvisited:
                    nodes_unvisited.remove(edge.dest)
                    node_stack.append(edge.dest)
                    traversal_list.append(edge.dest)
        return traversal_list
    # return (dfs) topological sorting of the nodes
    def topo_trav(self, graph):
        dfs_tree = DfsTree(graph)
        sorted_tuples = sorted(list(zip(dfs_tree.all_node_ids, dfs_tree.finish_time)), key=lambda time:time[1])
        sorted_node_ids = [tpl[0] for tpl in sorted_tuples]
        return list(reversed(sorted_node_ids))
                           
class DfsTree():
    def __init__(self, graph):
        self.graph = graph
        self.node_stack = []
        self.node_color = []
        self.discovery_time =[]
        self.finish_time = []
        self.predecessor = []
        self.time = 0
        self.all_node_ids = []
        for i in range(0, len(graph.nodes)):
            self.node_color.append('white')
            self.discovery_time.append(0)
            self.finish_time.append(0)
            self.predecessor.append(None)
            self.all_node_ids.append(graph.nodes[i].id)
        self.dfs()
    def dfs(self):
        for i in range(0, len(self.graph.nodes)):
            if self.node_color[self.graph.nodes[i].id] == 'white':
                self.dfs_visit(self.graph.nodes[i])
    def dfs_visit(self, node):
        # actual algorithm ..
        self.node_color[node.id] = 'gray'
        self.time += 1
        self.discovery_time[node.id] = self.time
        # the child nodes are directly stored as integers, so we can use them directly here 
        for edge in self.graph.edges[node.id]:
            if self.node_color[edge.dest] == 'white':
                self.predecessor[edge.dest] = node.id
                self.dfs_visit(self.graph.nodes[edge.dest])
        self.node_color[node.id] = 'black'
        self.time += 1
        self.finish_time[node.id] = self.time
    def print_results(self):
        # generate result lists
        finish = sorted(list(zip(self.all_node_ids, self.finish_time)), key=lambda time:time[1])
        disc = list(zip(self.all_node_ids, self.discovery_time))
        col = list(zip(self.all_node_ids, self.node_color))
        pre = list(zip(self.all_node_ids, self.predecessor))
        # print them
        print("SORTED FINISH TIMES:" + str(finish))
        print("DISCOVERY TIMES:" + str(disc))
        print("COLORS:" + str(col))
        print("PREDECESSORS:" + str(pre))
 
