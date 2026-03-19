"""
批量填充原始分类字段的脚本

从 raw_page_json 提取 category，从 pt_categories 获取分类名称
"""
import sqlite3
import json
import time


def main():
    db_path = 'data/nasfusion.db'

    # 连接数据库 - 增加超时时间
    conn = sqlite3.connect(db_path, timeout=60, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=60000")  # 60秒超时
    cursor = conn.cursor()

    # 获取 MTeam 站点 ID
    cursor.execute("SELECT id FROM pt_sites WHERE type = 'mteam'")
    mteam_site_ids = [row[0] for row in cursor.fetchall()]
    print(f"MTeam 站点 IDs: {mteam_site_ids}")

    if not mteam_site_ids:
        print("没有找到 MTeam 站点")
        return

    # 预加载所有分类名称到内存
    print("预加载分类映射...")
    category_map = {}
    for site_id in mteam_site_ids:
        cursor.execute(
            "SELECT category_id, name_chs FROM pt_categories WHERE site_id = ? AND is_active = 1",
            (site_id,)
        )
        for cat_id, name in cursor.fetchall():
            category_map[(site_id, str(cat_id))] = name

    print(f"加载了 {len(category_map)} 个分类映射")

    # 分批处理
    batch_size = 500  # 减小批量大小
    offset = 0
    total_updated = 0
    start_time = time.time()
    consecutive_errors = 0
    max_errors = 5

    while True:
        try:
            # 查询需要更新的记录
            site_ids_str = ','.join(str(sid) for sid in mteam_site_ids)
            cursor.execute(f"""
                SELECT id, site_id, raw_page_json
                FROM pt_resources
                WHERE site_id IN ({site_ids_str})
                  AND raw_page_json IS NOT NULL
                  AND (original_category_id IS NULL OR original_category_id = '')
                LIMIT {batch_size} OFFSET {offset}
            """)

            rows = cursor.fetchall()
            if not rows:
                print("没有更多记录需要处理")
                break

            # 准备批量更新数据
            updates = []
            for resource_id, site_id, raw_page_json in rows:
                try:
                    if isinstance(raw_page_json, str):
                        raw_data = json.loads(raw_page_json)
                    else:
                        raw_data = raw_page_json

                    category_id = raw_data.get('category')
                    if category_id:
                        category_id_str = str(category_id)
                        category_name = category_map.get((site_id, category_id_str))
                        updates.append((category_id_str, category_name, resource_id))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue

            # 批量更新 - 使用事务
            if updates:
                try:
                    cursor.execute("BEGIN IMMEDIATE")
                    cursor.executemany(
                        "UPDATE pt_resources SET original_category_id = ?, original_category_name = ? WHERE id = ?",
                        updates
                    )
                    cursor.execute("COMMIT")
                    consecutive_errors = 0  # 重置错误计数
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower():
                        print("数据库被锁定，等待后重试...")
                        time.sleep(2)
                        consecutive_errors += 1
                        if consecutive_errors >= max_errors:
                            print(f"连续错误过多，跳过本批次")
                            offset += batch_size
                            continue
                        continue  # 重试当前批次
                    else:
                        raise

            total_updated += len(updates)
            elapsed = time.time() - start_time
            speed = total_updated / elapsed if elapsed > 0 else 0

            # 计算剩余
            cursor.execute(f"""
                SELECT COUNT(*) FROM pt_resources
                WHERE site_id IN ({site_ids_str})
                  AND raw_page_json IS NOT NULL
                  AND (original_category_id IS NULL OR original_category_id = '')
            """)
            remaining = cursor.fetchone()[0]
            eta = remaining / speed if speed > 0 else 0

            print(f"已更新 {total_updated} 条记录 | 剩余: {remaining} | 速度: {speed:.0f} 条/秒 | 预计: {eta/60:.1f} 分钟")

            if len(rows) < batch_size:
                print("本批次记录数少于批量大小，可能已到末尾")
                break

            offset += batch_size

        except Exception as e:
            print(f"发生错误: {e}")
            consecutive_errors += 1
            if consecutive_errors >= max_errors:
                print(f"连续错误过多，停止处理")
                break
            time.sleep(5)
            continue

    print(f"\n迁移完成! 共更新 {total_updated} 条记录")

    # 验证结果
    cursor.execute("SELECT COUNT(*) FROM pt_resources WHERE original_category_id IS NOT NULL")
    filled = cursor.fetchone()[0]
    print(f"验证: 共有 {filled} 条记录有 original_category_id")

    cursor.execute("SELECT COUNT(*) FROM pt_resources WHERE original_category_name IS NOT NULL")
    named = cursor.fetchone()[0]
    print(f"验证: 共有 {named} 条记录有 original_category_name")

    # 查看分布
    cursor.execute("""
        SELECT original_category_id, original_category_name, COUNT(*) as cnt
        FROM pt_resources
        WHERE original_category_id IS NOT NULL
        GROUP BY original_category_id, original_category_name
        ORDER BY cnt DESC
        LIMIT 10
    """)
    print("\n分类分布:")
    for row in cursor.fetchall():
        print(f"  {row[0]} ({row[1]}): {row[2]} 条")

    conn.close()


if __name__ == "__main__":
    main()
