def countLines(filename):
  """Count the number of lines in a file.

  Args:
    filename: File to count lines of.

  Returns:
    Int value of the number of lines in a file.
  """
  try:
    with open(filename, 'r') as file:
      for i, l in enumerate(file):
        pass
    file.close()
    return i + 1
  except:
    return 0

def tailFile(filename, tailCount):
  """Trim a file to a set line count via tail.

  Args:
    filename: Name of file to trim.
    tailCount: Number of lines to trim to.
  """
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
      if len(line) > 0:
        newFile.write(line)
    newFile.close()
  else:
    oldFile.close()
    return 0