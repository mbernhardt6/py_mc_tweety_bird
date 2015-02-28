def countLines(filename):
  try:
    with open(filename, 'r') as file:
      for i, l in enumerate(file):
        pass
    file.close()
    return i + 1
  except:
    return 0

def tailFile(filename, tailCount):
  length = countLines(filename)
  oldFile = open(filename, 'r')
  start = length - (int(tailCount) + 1)
  if (start > 0):
    arrOutFile = []
    for i, line in enumerate(oldFile):
      if (i > start):
        arrOutFile.append(line)
    oldFile.close()
    newFile = open(filename, 'wb')
    for line in arrOutFile:
      newFile.write(line)
    newFile.close()
  else:
    oldFile.close()
    return 0