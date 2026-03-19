import sys
sys.path.insert(0, r'c:\07code\mem_server')
from src.config import get_settings
from src.memory.models import MemoryItem, MemoryType, ImportanceLevel
from src.memory.short_term import ShortTermMemoryManager
from src.memory.long_term import LongTermMemoryManager
from src.memory.assembler import ContextAssembler
from src.mcp_server import TOOLS
print("All imports OK")
print(f"MCP Tools: {len(TOOLS)}")
for t in TOOLS:
    print(f"  - {t.name}: {t.description[:50]}")

# 基础功能验证
s = get_settings()
stm = ShortTermMemoryManager(s)
ltm = LongTermMemoryManager(s)
assembler = ContextAssembler(stm, ltm)

# 添加一条规则
item = MemoryItem(
    session_id="global",
    memory_type=MemoryType.RULE,
    content="始终使用中文回答用户问题",
    importance=ImportanceLevel.HIGH,
)
rid = ltm.add_memory(item)
print(f"\nAdded rule: {rid[:8]}...")

# 添加profile
item2 = MemoryItem(
    session_id="global",
    memory_type=MemoryType.PROFILE,
    content="用户是一名Python开发者，偏好简洁直接的回答",
    importance=ImportanceLevel.MEDIUM,
)
pid = ltm.add_memory(item2)
print(f"Added profile: {pid[:8]}...")

stats = ltm.get_stats()
print(f"LTM stats: {stats}")
print("\nAll checks passed!")
