from matplotlib import pyplot as plt
import datetime

sequential_1000_log = open("sequential_1000.log", "r")
lines = sequential_1000_log.readlines()

start = 0
end = 0
x = []
y = []
i = 1
for line in lines[6:2006]:
    line = line.split()
    if line[2] == 'search':
        start = datetime.datetime.strptime(line[1], '%H:%M:%S.%f')
    else:
        end = datetime.datetime.strptime(line[1], '%H:%M:%S.%f')
        y.append((end - start).total_seconds())
        x.append(i)
        i += 1

plt.plot(x, y)
plt.xlabel('Request Number')
plt.ylabel('Time (s)')
plt.title('Time to process 1000 requests')
plt.savefig('sequential_1000_plot.png')

print("Average = ", sum(y)/len(y))
print("Max = ", max(y))
print("Min = ", min(y))
