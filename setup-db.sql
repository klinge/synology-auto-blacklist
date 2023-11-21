-- SCRIPT TO GENERATE AN EMPTY SQLITE3 DATABASE FOR TESTING
-- Database name on the Synology NAS is synoautoblock.db
DROP TABLE IF EXISTS "AutoBlockIP";
DROP INDEX IF EXISTS "result_deny_idx";
DROP INDEX IF EXISTS "result_expiretime_idx";

CREATE TABLE "AutoBlockIP" (
	"IP" VARCHAR(50) NOT NULL,
	"RecordTime" DATE NOT NULL,
	"ExpireTime" DATE NOT NULL,
	"Deny" TINYINT NOT NULL,
	"IPStd" UNKNOWN NOT NULL,
	"Type" INTEGER NULL,
	"Meta" VARCHAR(256) NULL,
	PRIMARY KEY ("IP")
);

CREATE INDEX "result_deny_idx" ON AutoBlockIP (Deny);
CREATE INDEX "result_expiretime_idx" ON AutoBlockIP (ExpireTime) ;
