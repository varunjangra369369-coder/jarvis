f = open('buildozer.spec', 'r')
data = f.read()
f.close()

lines = data.split('\n')
for i, line in enumerate(lines):
    # Match and update requirements setting
    if line.strip().startswith('requirements ='):
        lines[i] = 'requirements = python3, kivy, pyjnius, flask, requests'
    
    # Match and update storage permissions
    elif line.strip().startswith('#android.permissions =') or line.strip().startswith('android.permissions ='):
        lines[i] = 'android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE'
    
    # Match and update target Android API level
    elif line.strip().startswith('#android.api =') or line.strip().startswith('android.api ='):
        lines[i] = 'android.api = 33'
    
    # Match and enable automatic SDK license acceptance
    elif 'android.accept_sdk_license' in line:
        lines[i] = 'android.accept_sdk_license = True'

data = '\n'.join(lines)
f = open('buildozer.spec', 'w')
f.write(data)
f.close()
