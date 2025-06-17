from bot.persistence import get_storage
from bot.databases import userDB

store = get_storage()

# 1) create a tiny Users DB and save it
udb = userDB.UserDB()
udb.add_user("99", {"nickname": "TestPilot"})   # whatever API exists
store.save_users_db_raw(udb.serialize())

# 2) load it back through the same facade call
loaded_raw = store.get_users_db_raw()
udb2 = userDB.UserDB.deserialize(loaded_raw)

print("Nickname for UID 99 →", udb2.get_user("99")["nickname"])