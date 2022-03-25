import rpyc

c = rpyc.connect("localhost", 18861)
print(c.root.get_answer())
print(c.root.the_real_answer_though)

