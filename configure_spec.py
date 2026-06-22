f = open('buildozer.spec', 'r')
data = f.read()
f.close()

lines = data.split('\n')
for i, line in enumerate(lines):
    if line.startswith('requirements ='):
        lines[i] = 'requirements = python3, kivy, pyjnius, flask, requests'
    elif line.startswith('#android.permissions ='):
        lines[i] = 'android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE'
    elif line.startswith('#android.api ='):
        lines[i] = 'android.api = 33'

data = '\n'.join(lines)
f = open('buildozer.spec', 'w')
f.write(data)
f.close()
