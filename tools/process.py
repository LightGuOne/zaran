import os, sys
# 把 add_moran_aux_to_dict.py 中的函数直接复制过来，或者导入
from add_moran_aux_to_dict import getOnlyCharsTable, myDictProcess

if __name__ == "__main__":
    aux_path = "moran.chars.dict.yaml"   # 仓库根目录下的辅助码表
    input_dir = "input_dicts"
    output_dir = "dicts"
    aux_map = getOnlyCharsTable(aux_path)
    myDictProcess(input_dir, aux_map, output_dir)