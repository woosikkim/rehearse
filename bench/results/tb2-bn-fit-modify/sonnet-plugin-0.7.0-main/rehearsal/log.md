$ cd /app; ls -a; head -5 bn_sample_10k.csv; wc -l bn_sample_10k.csv; python3 -c 'import pgmpy;print(pgmpy.__version__)'; python3 -c 'import pandas,numpy,scipy;print(1)'
Exit code 1
.
..
.rehearsal
bn_sample_10k.csv
"U","Y","R","D","M"
65.1595787086976,55.0497451938166,73.1506268775402,57.6615550291927,64.3384681778361
44.6029054197735,43.600175682188,38.589412608575,45.9401940372555,21.2469494226791
54.4564237284025,54.1307611128149,47.302573583304,41.8194189531508,52.392400251044
57.3210008646862,61.0491365637276,48.9899101338243,54.4998895140635,52.223173316915
10001 bn_sample_10k.csv
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'pgmpy'
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'pandas'

$ cd /app; pip install pandas numpy scipy 2>&1 | tail -1; python3 -I -c 'import pandas as pd;d=pd.read_csv("bn_sample_10k.csv");print(d.corr().round(3));import numpy as np;print(np.round(np.linalg.inv(d.corr().values),2))'
Exit code 1
hint: See PEP 668 for the detailed specification.
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'pandas'

$ cd /app; pip install --break-system-packages pandas numpy scipy 2>&1 | tail -1; python3 -I -c 'import pandas as pd;d=pd.read_csv("bn_sample_10k.csv");print(d.corr().round(3));import numpy as np;print(np.round(np.linalg.inv(d.corr().values),2))'
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv
       U      Y      R      D      M
U  1.000  0.603  0.704  0.537  0.662
Y  0.603  1.000  0.431  0.539  0.385
R  0.704  0.431  1.000  0.382  0.599
D  0.537  0.539  0.382  1.000  0.348
M  0.662  0.385  0.599  0.348  1.000
[[ 3.17 -0.78 -1.14 -0.52 -0.94]
 [-0.78  1.75 -0.03 -0.53  0.04]
 [-1.14 -0.03  2.12 -0.01 -0.5 ]
 [-0.52 -0.53 -0.01  1.57  0.01]
 [-0.94  0.04 -0.5   0.01  1.9 ]]

