basedict={}
with open(r'g:\Rime\rime_20251227\dicts\other\魔然简词库缩写.dict1.yaml', 'r', encoding='utf-8') as inputFile:
    for line in inputFile:
        lineSplit=line.split('\t')
        basedict[lineSplit[0]]=lineSplit[1]
        pass

# print('完成')
# print(basedict['暗渡陈仓'])

with open(r'g:\Rime\rime_20251227\moran_fixed_simp.dict.yaml', 'r', encoding='utf-8') as inputFile1,\
    open(r'g:\Rime\rime_20251227\dicts\other\错误码20260226.yaml', 'w', encoding='utf-8') as outFile:
    for _ in range(30):
        # next(inputFile1)  # 或 f.readline()
        inputFile1.readline()
    for line in inputFile1:
        # print(line)
        lineSplit=line.split('\t')
        if len(lineSplit)<2:
            continue
        lineText=lineSplit[0]
        lineCode=lineSplit[1].strip()
        trueCode=basedict.get(lineText,'无结果')
        if trueCode != lineCode and trueCode !='无结果' and len(lineText)==3:
            # print(lineText,trueCode,lineCode,len(trueCode),len(lineCode))
            outFile.write(f'{lineText}\t{lineCode}\t{trueCode}\n')
            # outFile.write(line)
            # break
        pass