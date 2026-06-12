"""
世界线收束序列 Worldline Convergence Sequence
研学定稿全域公开代码｜适配对外发表
迭代规则：全域字符计频 + 从左至右首次出现顺序拼接
全域适配：支持数字、大小写字母、特殊符号、混合字符种子
核心特性：任意初始原点，最终必然收敛至固定宿命闭环
交互升级：节点行数可选输入，为空回车自动推演至完整收束闭环
"""


def _get_next_node(current: str) -> str:
    """
    【内部工具函数】单步推演生成下一个世界线节点
    统一迭代逻辑，全程序唯一一处迭代规则定义
    :param current: 当前世界线节点字符串
    :return: 推演后的下一节点字符串
    """
    # 全域统计任意字符出现频次
    char_count = {}
    for ch in current:
        char_count[ch] = char_count.get(ch, 0) + 1

    # 从左到右记录字符首次出现顺序，去重保原生顺序
    appear_order = []
    existed = set()
    for ch in current:
        if ch not in existed:
            existed.add(ch)
            appear_order.append(ch)

    # 按既定顺序拼接：频次+本位字符，生成下一世界线节点
    return ''.join(str(char_count[char]) + char for char in appear_order)


def worldline_convergence_seq(origin_seed, rows=None):
    """
    世界线节点生成主函数
    :param origin_seed: 初始世界线原点种子，任意字符均可
    :param rows: 自定义推演节点数，None=自动推演至收束闭环
    :return: 完整世界线节点推演列表
    """
    current = str(origin_seed)
    result = [current]

    # 参数合法性校验
    if rows is not None:
        if not isinstance(rows, int) or rows < 1:
            raise ValueError("推演节点数必须为正整数")

        # 手动指定行数：按指定条数迭代
        for _ in range(rows - 1):
            current = _get_next_node(current)
            result.append(current)
        return result

    # 未输入行数：自动全速推演，直至出现重复节点（完成收束）
    history = {current: 0}
    history_list = [current]
    while True:
        next_node = _get_next_node(current)
        history_list.append(next_node)
        # 节点重复，世界线完成收束，终止推演
        if next_node in history:
            break
        history[next_node] = len(history_list) - 1
        current = next_node
    return history_list


def detect_worldline_cycle(origin_seed, max_check=2000):
    """
    自动收束检测函数：识别分歧域、命运闭环、闭环周期
    :param origin_seed: 初始世界线原点种子
    :param max_check: 最大推演步数，防止极端场景无限运行
    :return: (分歧世界域列表, 命运闭环列表, 闭环周期长度)
    """
    current = str(origin_seed)
    # 字典存储节点与索引映射，O(1)查重与定位
    node_index_map = {}
    history_node = []

    while len(history_node) < max_check:
        # 检索历史节点，判定世界线收束
        if current in node_index_map:
            converge_pos = node_index_map[current]
            branch_world = history_node[:converge_pos]   # 分歧世界域
            fate_cycle = history_node[converge_pos:]     # 命运收束闭环
            return branch_world, fate_cycle, len(fate_cycle)

        node_index_map[current] = len(history_node)
        history_node.append(current)
        current = _get_next_node(current)

    # 达到最大步数仍未收束（理论上不会触发，作为安全兜底）
    return history_node, [], 0


# 对外公开交互主控程序【升级可选输入】
if __name__ == "__main__":
    # 全字符开放输入，无格式限制
    seed = input("请输入世界线初始原点种子(支持数字/字母/符号/混合字符)：")
    row_input = input("请输入需推演节点数量【直接回车=自动推演至世界线收束完成】：").strip()

    # 判定输入：空输入自动全速推演，非空输入按指定行数推演
    try:
        if row_input == "":
            worldline_log = worldline_convergence_seq(seed, rows=None)
        else:
            rows = int(row_input)
            worldline_log = worldline_convergence_seq(seed, rows=rows)
    except ValueError as e:
        print(f"\n输入错误：{e}，已自动切换为完整收束推演模式")
        worldline_log = worldline_convergence_seq(seed, rows=None)

    # 生成完整世界线推演日志
    print("\n===世界线推演日志===")
    for idx, node in enumerate(worldline_log, 1):
        print(f"第{idx}世界线节点：{node}")

    # 输出专业收束研判报告
    branch_domain, fate_loop, loop_len = detect_worldline_cycle(seed)
    print("\n===世界线收束研判报告===")
    print(f"分歧世界域节点总数：{len(branch_domain)}")
    print(f"世界线正式收束起始：第{len(branch_domain)+1}节点")
    print(f"命运闭环周期长度：{loop_len}")
    print(f"既定宿命闭环内容：{fate_loop}")
    print(f"世界线正式收束节点：{fate_loop[-1]}")