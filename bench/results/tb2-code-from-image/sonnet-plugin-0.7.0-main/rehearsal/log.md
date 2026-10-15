$ python3 -I -c '
import hashlib,sys
h=hashlib.sha256(sys.stdin.buffer.read()).digest()
x=h.hex().encode()
print("A",hashlib.sha256(h+h[:10]+b"0000TBENCH-SALT").hexdigest())
print("B",hashlib.sha256(x+x[:10]+b"0000TBENCH-SALT").hexdigest())
print("C",hashlib.sha256(h+x[:10]+b"0000TBENCH-SALT").hexdigest())
print("D",hashlib.sha256(h+h[:10]+b"OOOOTBENCH-SALT").hexdigest())
print("E",hashlib.sha256(x+x[:10]+b"OOOOTBENCH-SALT").hexdigest())
' < /app/code.png
A bee26a133f103b9ecda444c70ec22cafef6e31a3de7af6d047974dc90ce3defe
B 4189c1e4367244d74d5bbff1aeb4bd1f85e9d3c7c59643dd381f072cf767a268
C 5ce0021d1ce1b3dd3f7ee297dde60df3356bc960ba3f57e90ee47400958f66b1
D 606da3111cd536d79550e1dc5c8e96923ab07b51d60096291e5758ba36c1de5e
E e3a14fba783f0c78e5637059ecf44751c27af7cf434d2d27e46e8ddc2c7cdb69

$ printf 'bee26a133f103b9ecda444c70ec22cafef6e31a3de7af6d047974dc90ce3defe\n' > /app/output.txt; cat /app/output.txt
bee26a133f103b9ecda444c70ec22cafef6e31a3de7af6d047974dc90ce3defe

