import pickle

def load_pickle(file_path):
    """从 .pkl 文件加载数据。

    Args:
        file_path (str): .pkl 文件的路径。

    Returns:
        从文件加载的数据。
    """
    try:
        with open(file_path, 'rb') as file:  # 'rb' 模式用于读取二进制文件
            data = pickle.load(file)
        return data
    except FileNotFoundError:
        print(f"错误：在 {file_path} 找不到文件")
        return None
    except Exception as e:
        print(f"发生错误：{e}")
        return None

# 示例用法：
file_path = r'E:\CS\Graphics\bedlam_render\renderpeople_mixamo_labels_with_original.pkl'  # 替换为 .pkl 文件的实际路径
data = load_pickle(file_path)

if data:
    print("数据加载成功：")
    if isinstance(data, list):
        print("数据类型：列表")
        for i in range(min(5, len(data))):  # 打印前 5 个元素
            print(f"元素 {i}: {data[i]}")
    elif isinstance(data, dict):
        print("数据类型：字典")
        keys = list(data.keys())
        #for i in range(min(5, len(keys))): # 打印前 5 个键值对
        #    print(f"键 {i}: {keys[i]}")
        #    key = keys[i]
        #    #print(f"键 {key}: {data[key]}")
        for key in keys:
            if key == 'data_list':
                if isinstance(data[key], dict):
                    print(f"键 {key} 的数据类型：字典")
                    new_key_0 = list(data[key].keys())[0] if data[key] else None
                    if new_key_0:
                        print(f"键 {new_key_0}")
                        # check its value type
                        data_0 = data[key][new_key_0] # dict
                        for sub_key, sub_value in data_0.items():
                            if sub_key == "Push" :
                                print(f"子键 {sub_key} 的数据类型：{type(sub_value)}") # list
                                print(f"子键 {sub_key} 的前 1 个元素：{sub_value[:1] if isinstance(sub_value, list) else sub_value}")
            else:
                print(f"键 {key} 的 value : {data[key]}")  
    else:
        print(f"数据类型：{type(data)}")
        print("无法直接查看部分数据，请根据数据类型选择合适的方法。")