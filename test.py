class isis_entry:
	def __init__(self, name, neighbors,):
		self.name = name[:-3]
		self.neighbors = neighbors



isis_detail = open("isis_detail.txt")
isis_summary = open("isis.txt")

isis_detail = isis_detail.readlines()
isis_summary = isis_summary.readlines()

#cleaup
isis_sum = []
isis_det = []
isis_idx = []

for i in isis_detail: 
	i = i.lstrip()
	isis_det.append(i)

for i in isis_summary:
	i = i.lstrip().split(' ')[0]
	isis_sum.append(i)

for i, j in enumerate(isis_det): 
	for a in isis_sum:
		if a in j:
			isis_idx.append(i)



isis_idx.append(len(isis_det))

#[0, 12, 22, 32, 49, 64, 76, 86]


#partition isis detail 
isis_det_partition = []
for i, j in enumerate(isis_idx[:-1]):
	batch_list = []
	current_idx = j
	next_idx = isis_idx[i+1]
	isis_det_partition.append(isis_det[current_idx:next_idx])


#example isis detail
#['BBTPNJ51-G6-Arista1.00-00 7274      3897   1018  L1 <>\n', 'LSP generation remaining wait time: 0 ms\n', 'NLPID: 0xCC(IPv4)\n', 
#'Hostname: BBTPNJ51-G6-Arista1\n', 'Area address: 49.0000\n', 'Interface address: 192.168.17.59\n', 'Interface address: 192.168.17.57\n', 
#'Interface address: 172.16.10.7\n', 'IS Neighbor          : BBTPNJ33F11-SP1-Lab.00 Metric: 10\n', 
#'Reachability         : 192.168.17.58/31 Metric: 10 Type: 1 Up\n', 'Reachability         : 192.168.17.56/31 Metric: 10 Type: 1 Up\n', 
#'Reachability         : 172.16.10.7/32 Metric: 10 Type: 1 Up\n']

#create a list of neighbor objects

isis_entry_list = []


for neighbor in isis_det_partition:
	class_name = neighbor[0].split(" ")[0] 
	class_neighbor = []
	for entry in neighbor:
		if "IS Neighbor" in entry:
			class_neighbor.append(entry)
	isis_entry_list.append(isis_entry(class_name, class_neighbor))


for entry in isis_entry_list: 
	print entry.name
	print entry.neighbors



		



