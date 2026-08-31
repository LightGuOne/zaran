import os, shutil,re, zipfile, tempfile
from typing import Dict, List
from zrmify import zrmify
from tqdm import tqdm


# TODO: 辅助码处理 - 读取辅助码表并刷写入编码
def getOnlyCharsTable(auxFilePath: str) -> dict:
    """获取第一项辅助码

    :param auxFilePath: moran.char.dict.yaml文件路径
    :return: 唯一辅助码的对应字典
    """
    aux_map = {}
    seen_keys = set()  # 用于记录已经出现过的键

    with open(auxFilePath, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()

    # 分离普通行和偏旁部首行
    normal_lines = []
    pianpan_lines = []
    in_pianpan = False

    for line in all_lines:
        if line.startswith('# 偏旁部首'):
            in_pianpan = True
            continue
        if line.startswith('# 符號'):
            in_pianpan = False
            continue
        if in_pianpan:
            pianpan_lines.append(line)
        else:
            normal_lines.append(line)

    # 先处理普通行，再处理偏旁部首行（使偏旁部首的辅助码覆盖同字符的普通行）
    for line in normal_lines + pianpan_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        parts = line.split('\t')
        if len(parts) < 2:
            continue
        char = parts[0]
        aux_code=parts[1].split(';', 1)[1]

        # 去重（如果字符已存在，则跳过，否则添加）
        if char in seen_keys:
            continue
        seen_keys.add(char)
        aux_map[char] = aux_code

    return aux_map

def refresh_aux(cols: List[str], word: str, aux_map: Dict[str, str], userdb: bool, process_pinyin: bool=True):
    """刷辅助码

    :param cols: 待处理编码
    :param word: 候选文本
    :param aux_map: 辅助码表
    :param userdb: 是否为userdb文件
    :return: _description_
    """
    seg_idx = 0 if userdb else 1
    if not userdb and len(cols) == 1:
        cols.insert(1, '')
    if userdb and len(cols) < 2:
        cols.append('')

    raw_segs = cols[seg_idx].strip().split() if seg_idx < len(cols) else []
    aux_segs = [aux_map.get(字, '') for 字 in word]  # 行级处理 

    merged = []
    for i, py in enumerate(raw_segs):
        aux = aux_segs[i] if i < len(aux_segs) else ''
        py=py.split(';')[0]
        if process_pinyin:
            py=re.sub(pattern,lambda x:patternLsit[x.group(0)],py)
            try:
                py = zrmify(py)
            except ValueError:
                py = {'ng': 'eg', 'm': 'mm'}.get(py, py)   # 嗯→eg、呣/呒→mm（自然码零声母双写）
        merged.append(f"{py};{aux}")
    if userdb:
        cols[0] = ' '.join(merged)
    else:
        cols[seg_idx] = ' '.join(merged)

    return cols


# TODO: 词库处理 - 按策略配置批量处理词库
def process_single_file(src: str, dst: str, aux_map: Dict[str, str]):
    """处理词库文件，刷入辅助码"""
    userdb = False
    
    with open(src, 'r', encoding='utf-8') as inputFile, open(dst, 'w', encoding='utf-8') as outputFile:
        seen = set()   # 记录 (候选词, 编码) 组合
        for line in inputFile:
            outputFile.write(line)
            if '#@/db_type' in line:
                userdb = True
            if line.startswith('...') or line.startswith('#@/user_id'):
                break


        for line in inputFile:
            if line.startswith('#') or not line.strip():
                outputFile.write(line)
                continue

            # 处理词条
            cols = line.rstrip('\n').split('\t')
            word = cols[1] if userdb else cols[0]
            cols = refresh_aux(cols, word, aux_map, userdb)

            # 去重：(候选词, 处理后的编码) 已出现过则丢弃，忽略权重
            key = (word, cols[0 if userdb else 1])
            if key in seen:
                continue
            seen.add(key)

            # 用户词典特殊处理
            if userdb and not cols[0].endswith(' '):
                cols[0] += ' '
            
            outputFile.write('\t'.join(cols) + '\n')



# ---- 操作类型常量 ----
SKIP = 0      # 跳过，不处理
PASS = 1      # 直接复制，不做转换
PROCESS = 2   # 调用 process_single_file 处理

# ---- 词库处理配置 ----
# 格式: 文件名 -> 操作类型
processDict = {
    'chengyu.txt':                    SKIP,
    'en.dict.yaml':                   SKIP,
    'wuzhong.pro.dict.yaml':          SKIP,
    'cn&en.dict.yaml':                SKIP,
    'renming.pro.dict.yaml':          SKIP,

    'cuoyin.pro.dict.yaml':           PROCESS,
    'diming.pro.dict.yaml':           PROCESS,
    'duoyin.pro.dict.yaml':           PROCESS,
    'jichu.pro.dict.yaml':            PROCESS,
    'lianxiang.pro.dict.yaml':        PROCESS,
    'shici.pro.dict.yaml':            PROCESS,

    'zi.pro.dict.yaml':               PROCESS,
    'cuoyin.dict.yaml':           PROCESS,
    'diming.dict.yaml':           PROCESS,
    'duoyin.dict.yaml':           PROCESS,
    'jichu.dict.yaml':            PROCESS,
    'lianxiang.dict.yaml':        PROCESS,
    'shici.dict.yaml':            PROCESS,
    'zi.dict.yaml':               PROCESS,
    'rime_wanxiang.userdb.txt':       PROCESS,
    'zaran.userdb.txt':       PROCESS,
}

patternLsit={
    'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a', 
    'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o', 
    'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e', 
    'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i', 
    'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u', 
    'ǖ': 'v', 'ǘ': 'v', 'ǚ': 'v', 'ǜ': 'v', 'ü': 'v',
    'ń':'n','ň':'n','ǹ':'n','ḿ':'m','\u0300': ''
    }
pattern=re.compile('[āáǎàōóǒòēéěèīíǐìūúǔùǖǘǚǜüńňǹḿ\u0300]')

# 未在字典中的文件默认操作
DEFAULT_ACTION = SKIP   # 默认跳过
desktop_path=os.path.expanduser(r'~\desktop')

def myDictProcess(input_path, aux_map,
                outputPath=os.path.join(desktop_path, 'process_output')):
    """
    批量处理输入目录下的词库文件。
    - input_path : 原始词库目录
    - aux_map    : 辅助码表（供 process_single_file 使用）
    - outputPath : 输出目录（默认 ~/process_output）
    """
    # 安全创建输出目录
    os.makedirs(outputPath, exist_ok=True)

    files = os.listdir(input_path)
    progress = tqdm(files, total=len(files), ncols=90, desc="处理词库")

    for fileName in progress:
        filePath = os.path.join(input_path, fileName)

        if not os.path.isfile(filePath):
            progress.set_postfix_str(f"跳过非文件: {fileName}")
            continue

        action = processDict.get(fileName, DEFAULT_ACTION)
        dstPath = os.path.join(outputPath, os.path.basename(filePath))

        try:
            if action == PROCESS:
                process_single_file(filePath, dstPath, aux_map)
                progress.set_postfix_str(f"已处理: {fileName}")
            elif action == PASS:
                shutil.copy(filePath, dstPath)
                progress.set_postfix_str(f"已复制: {fileName}")
            else:  # SKIP
                progress.set_postfix_str(f"已跳过: {fileName}")
        except Exception as e:
            progress.set_postfix_str(f"失败: {fileName} - {str(e)}")
            continue


if __name__ == "__main__":
    # TODO: 主流程 - 定位解压词库并执行批量处理
    zip_path=None
    zipFileList=['base-dicts.zip',
                'pro-zrm-fuzhu-dicts.zip'
                ]
    for i in zipFileList:
        path=os.path.join(desktop_path,i)
        if os.path.exists(path):
            zip_path=path
            break

    # 获取魔然单字表的相对路径
    auxFilePath = os.path.join(os.path.dirname(os.path.dirname(__file__)),'moran.chars.dict.yaml')
    if not zip_path:
        input_path=r'dicts'   # 临时处理一下
        charsTable = getOnlyCharsTable(auxFilePath)  # 获取唯一辅助码
        myDictProcess(input_path, charsTable)        # 处理词库替换辅助码
    else:
        zipName = os.path.splitext(os.path.basename(zip_path))[0]
        # 使用临时目录，with块结束后自动删除
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    # 跳过目录
                    if file.endswith('/'):
                        continue
                    # 只处理目标文件夹下的文件（压缩包内通常有顶层文件夹）
                    if not file.startswith(zipName + '/'):
                        continue

                    # 提取到临时目录，保持原有内部路径
                    zip_ref.extract(file, tmpdir)

            # 实际需要处理的路径是临时目录下的顶层文件夹
            input_path = os.path.join(tmpdir, zipName)

            # 后续处理
            charsTable = getOnlyCharsTable(auxFilePath)  # 获取唯一辅助码
            myDictProcess(input_path, charsTable)        # 处理词库替换辅助码
            # 退出with块，临时目录及其所有内容自动删除