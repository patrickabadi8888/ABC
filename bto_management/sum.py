import glob

# print all files and their contents in the format recursive
# # File name
#  File content
# ----
s = ''
for filename in glob.glob('*.py'):
    s += f'# File name: {filename}\n'
    
    with open(filename, 'r') as f:
        content = f.read()
        s += f'{content}\n'
    s += '----\n'

with open('all_files.txt', 'w') as f:
    f.write(s)