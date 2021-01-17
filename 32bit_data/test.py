f = open("C:/Users/82106/Desktop/trading_example/32bit_data/" + "test" + ".csv", "r", encoding="utf8")


lines = f.readlines()
print(len(lines))

code = lines[0]
print(code.strip())

f.close()