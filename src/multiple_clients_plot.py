from matplotlib import pyplot as plt

multiple_clients_log = open("multiple_clients_4.log", "r")
lines = multiple_clients_log.readlines()

start = 0
end = 0
b0x = [1]
b0y = []
b1x = [1]
b1y = []
b2x = [1]
b2y = []
b3x = [1]
b3y = []
for line in lines[9:]:
    line = line.split()
    if line[1] == 'buyer0' and len(b0y) < 30:
        b0y.append(float(line[0]))
        if len(b0y) > 1:
            b0x.append(b0x[-1] + 1)
    elif line[1] == 'buyer1' and len(b1y) < 30:
        b1y.append(float(line[0]))
        if len(b1y) > 1:
            b1x.append(b1x[-1] + 1)
    elif line[1] == 'buyer2' and len(b2y) < 30:
        b2y.append(float(line[0]))
        if len(b2y) > 1:
            b2x.append(b2x[-1] + 1)
    elif line[1] == 'buyer3' and len(b3y) < 30:
        b3y.append(float(line[0]))
        if len(b3y) > 1:
            b3x.append(b3x[-1] + 1)

# print(b1x)
# print(b1y)
plt.plot(b0x, b0y, label = 'buyer0')
plt.plot(b1x, b1y, label = 'buyer1')
plt.plot(b2x, b2y, label = 'buyer2')
plt.plot(b3x, b3y, label = 'buyer3')
plt.xlabel('Request Number')
plt.ylabel('Time (s)')
plt.title('Time to process 30 requests')
plt.legend()
plt.savefig('multiple_clients_4.png')

print("Average b0 = ", sum(b0y)/len(b0y))
print("Average b1 = ", sum(b1y)/len(b1y))
print("Average b2 = ", sum(b2y)/len(b2y))
print("Average b3 = ", sum(b3y)/len(b3y))