-- =========================================================================
-- SmartReach AI - full database schema
-- AUTO-GENERATED from the ORM models on 2026-09-14 - DO NOT EDIT BY HAND.
-- Regenerate after model changes:  cd backend && python generate_schema_sql.py
--
-- Re-runnable: CREATE TABLE IF NOT EXISTS + FK checks disabled during run.
-- Compatible with MySQL 8.x and MariaDB 10.1+ (utf8mb4, 191-char index caps).
-- Usage: mysql -u <user> -p <database> < database/schema_full.sql
-- See database/README.md for when and how to run this.
-- =========================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ---- users -------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	email VARCHAR(191) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	name VARCHAR(255), 
	`role` ENUM('admin','user') NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	last_login DATETIME, 
	is_active BOOL NOT NULL, 
	plan VARCHAR(50) NOT NULL DEFAULT 'free', 
	billing_status VARCHAR(50) NOT NULL DEFAULT 'active', 
	billing_notes TEXT, 
	PRIMARY KEY (id),
	UNIQUE KEY ix_users_email (email)
)ENGINE=InnoDB CHARSET=utf8mb4;

-- ---- campaigns ---------------------------------------------------
CREATE TABLE IF NOT EXISTS campaigns (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	status ENUM('draft','researching','ready','active','paused','completed') NOT NULL, 
	keywords TEXT NOT NULL, 
	settings TEXT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	started_at DATETIME, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	KEY ix_campaigns_user_id (user_id)
)ENGINE=InnoDB CHARSET=utf8mb4;

-- ---- leads -------------------------------------------------------
CREATE TABLE IF NOT EXISTS leads (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	campaign_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	keyword VARCHAR(255) NOT NULL, 
	source_url TEXT NOT NULL, 
	contact_page_url TEXT, 
	organization_name VARCHAR(255) NOT NULL, 
	website VARCHAR(255) NOT NULL, 
	contact_name VARCHAR(255), 
	job_title VARCHAR(255), 
	department VARCHAR(255), 
	email VARCHAR(255), 
	phone VARCHAR(255), 
	country VARCHAR(100), 
	city VARCHAR(100), 
	lead_score INTEGER NOT NULL, 
	ai_reasoning TEXT, 
	status ENUM('new','researching','qualified','review','approved','rejected','scheduled','sent','replied','interested','not_interested','unsubscribed','bounced','do_not_contact') NOT NULL, 
	generated_email TEXT, 
	email_template_id INTEGER, 
	emails_sent INTEGER NOT NULL, 
	follow_up_count INTEGER NOT NULL, 
	last_emailed_at DATETIME, 
	do_not_contact BOOL NOT NULL, 
	unsubscribed_at DATETIME, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	qualified_at DATETIME, 
	approved_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	KEY ix_leads_campaign_id (campaign_id),
	KEY ix_leads_user_id (user_id)
)ENGINE=InnoDB CHARSET=utf8mb4;

-- ---- research_results --------------------------------------------
CREATE TABLE IF NOT EXISTS research_results (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	campaign_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	keyword VARCHAR(255) NOT NULL, 
	url TEXT NOT NULL, 
	domain VARCHAR(191) NOT NULL, 
	title VARCHAR(512), 
	snippet TEXT, 
	status ENUM('discovered','queued','crawling','crawled','skipped','failed') NOT NULL, 
	provider VARCHAR(50), 
	result_position INTEGER, 
	extra_data TEXT, 
	error_message TEXT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	crawled_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	KEY ix_research_results_campaign_id (campaign_id),
	KEY ix_research_results_domain (domain),
	KEY ix_research_results_status (status),
	KEY ix_research_results_user_id (user_id)
)ENGINE=InnoDB CHARSET=utf8mb4;

-- ---- emails ------------------------------------------------------
CREATE TABLE IF NOT EXISTS emails (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	campaign_id INTEGER NOT NULL, 
	lead_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	to_email VARCHAR(255) NOT NULL, 
	from_email VARCHAR(255) NOT NULL, 
	subject VARCHAR(255) NOT NULL, 
	body TEXT NOT NULL, 
	status ENUM('sent','failed','bounced') NOT NULL, 
	provider VARCHAR(50), 
	error_message TEXT, 
	message_id VARCHAR(255), 
	unsubscribe_token VARCHAR(64), 
	sent_at DATETIME, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	KEY ix_emails_campaign_id (campaign_id),
	KEY ix_emails_lead_id (lead_id),
	KEY ix_emails_status (status),
	KEY ix_emails_user_id (user_id)
)ENGINE=InnoDB CHARSET=utf8mb4;

-- ---- replies -----------------------------------------------------
CREATE TABLE IF NOT EXISTS replies (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	campaign_id INTEGER NOT NULL, 
	lead_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	from_email VARCHAR(255) NOT NULL, 
	from_name VARCHAR(255), 
	subject VARCHAR(255), 
	body TEXT NOT NULL, 
	category ENUM('interested','not_interested','need_more_info','request_meeting','pricing_request','out_of_office','unsubscribe','wrong_contact','other') NOT NULL, 
	ai_summary TEXT, 
	classification_error VARCHAR(255), 
	status ENUM('unread','read') NOT NULL, 
	in_reply_to VARCHAR(191), 
	received_at DATETIME, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (in_reply_to),
	KEY ix_replies_campaign_id (campaign_id),
	KEY ix_replies_category (category),
	KEY ix_replies_lead_id (lead_id),
	KEY ix_replies_user_id (user_id)
)ENGINE=InnoDB CHARSET=utf8mb4;

-- ---- suppressions ------------------------------------------------
CREATE TABLE IF NOT EXISTS suppressions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	email VARCHAR(190) NOT NULL, 
	reason ENUM('unsubscribed','bounced','manual') NOT NULL, 
	lead_id INTEGER, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_suppression_user_email UNIQUE (user_id, email), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE SET NULL,
	KEY ix_suppressions_email (email),
	KEY ix_suppressions_user_id (user_id)
)ENGINE=InnoDB CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
