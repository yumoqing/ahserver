
from sqlor.dbpools import runSQL

async def getFilenameFromId(idstr:str) -> str:
	sql = "select * from kvobjects where id='%s'" % idstr
	recs = await runSQL('homedata',sql)
	if recs is None:
		return None
	if len(recs) == 0:
		return None
	return recs[0].name

