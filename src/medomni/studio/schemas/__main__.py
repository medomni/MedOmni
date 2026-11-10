from medomni.studio.schemas import write

for p in write():
    print(p.name)
