-- ==============================================================================
-- KAMPALA UNIVERSITY ONLINE VOTING SYSTEM (KU-OVS)
-- Comprehensive Production MySQL Database Schema
-- Compatible with MySQL 5.7+ / 8.0+ / MariaDB 10.3+
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS `ku_voting` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `ku_voting`;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `audit_logs`;
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `faqs`;
DROP TABLE IF EXISTS `votes`;
DROP TABLE IF EXISTS `voter_participation`;
DROP TABLE IF EXISTS `eligibility_rules`;
DROP TABLE IF EXISTS `candidates`;
DROP TABLE IF EXISTS `positions`;
DROP TABLE IF EXISTS `elections`;
DROP TABLE IF EXISTS `admins`;
DROP TABLE IF EXISTS `students`;
DROP TABLE IF EXISTS `university_records`;
SET FOREIGN_KEY_CHECKS = 1;

-- ==============================================================================
-- 1. UNIVERSITY REGISTRAR RECORDS
-- Authoritative student roster maintained by the university administration.
-- Used to verify students upon self-registration.
-- ==============================================================================
CREATE TABLE `university_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` VARCHAR(50) NOT NULL UNIQUE COMMENT 'Official KU Student ID e.g. KU/2024/001',
    `reg_no` VARCHAR(50) NOT NULL UNIQUE COMMENT 'Official Registration Number',
    `full_name` VARCHAR(150) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `campus` VARCHAR(100) NOT NULL COMMENT 'Ggaba (Main), Old Kampala, Luweero, Jinja, Masaka',
    `faculty` VARCHAR(150) NOT NULL,
    `course` VARCHAR(150) NOT NULL,
    `year_of_study` INT NOT NULL DEFAULT 1,
    `gender` ENUM('Male', 'Female', 'Other') NOT NULL DEFAULT 'Other',
    `is_registered_student` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_uni_campus` (`campus`),
    INDEX `idx_uni_faculty` (`faculty`),
    INDEX `idx_uni_course` (`course`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 2. STUDENTS (AUTHENTICATED VOTERS)
-- Registered student accounts that have completed verification.
-- ==============================================================================
CREATE TABLE `students` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` VARCHAR(50) NOT NULL UNIQUE,
    `reg_no` VARCHAR(50) NOT NULL UNIQUE,
    `full_name` VARCHAR(150) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `campus` VARCHAR(100) NOT NULL,
    `faculty` VARCHAR(150) NOT NULL,
    `course` VARCHAR(150) NOT NULL,
    `year_of_study` INT NOT NULL DEFAULT 1,
    `gender` ENUM('Male', 'Female', 'Other') NOT NULL DEFAULT 'Other',
    `is_verified` BOOLEAN NOT NULL DEFAULT TRUE,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `last_login` DATETIME NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_student_campus` (`campus`),
    INDEX `idx_student_faculty` (`faculty`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 3. ADMINS & ELECTORAL COMMISSION (EC) OFFICIALS
-- System administrators and Electoral Commission members with role-based access.
-- ==============================================================================
CREATE TABLE `admins` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(80) NOT NULL UNIQUE,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `full_name` VARCHAR(150) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('super_admin', 'ec_chair', 'ec_commissioner', 'auditor') NOT NULL DEFAULT 'ec_commissioner',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `last_login` DATETIME NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 4. ELECTIONS
-- Election events with status transitions and scheduling windows.
-- ==============================================================================
CREATE TABLE `elections` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT NULL,
    `academic_year` VARCHAR(20) NOT NULL COMMENT 'e.g. 2025/2026',
    `start_time` DATETIME NOT NULL,
    `end_time` DATETIME NOT NULL,
    `status` ENUM('draft', 'scheduled', 'active', 'paused', 'closed', 'results_published') NOT NULL DEFAULT 'draft',
    `results_approved_by` INT NULL,
    `results_approved_at` DATETIME NULL,
    `created_by` INT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_election_creator` FOREIGN KEY (`created_by`) REFERENCES `admins`(`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_election_approver` FOREIGN KEY (`results_approved_by`) REFERENCES `admins`(`id`) ON DELETE SET NULL,
    INDEX `idx_election_dates` (`start_time`, `end_time`),
    INDEX `idx_election_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 5. POSITIONS
-- Offices contested in an election (e.g., Guild President, Faculty Rep).
-- ==============================================================================
CREATE TABLE `positions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `election_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `description` TEXT NULL,
    `max_selections` INT NOT NULL DEFAULT 1,
    `priority_order` INT NOT NULL DEFAULT 1,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_position_election` FOREIGN KEY (`election_id`) REFERENCES `elections`(`id`) ON DELETE CASCADE,
    INDEX `idx_position_election` (`election_id`, `priority_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 6. CANDIDATES
-- Candidates running for specific positions with manifesto and campaign visuals.
-- ==============================================================================
CREATE TABLE `candidates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `election_id` INT NOT NULL,
    `position_id` INT NOT NULL,
    `student_id` VARCHAR(50) NULL COMMENT 'Optional link to student identifier',
    `full_name` VARCHAR(150) NOT NULL,
    `course` VARCHAR(150) NOT NULL,
    `campus` VARCHAR(100) NOT NULL,
    `photo_url` VARCHAR(255) NULL,
    `symbol_url` VARCHAR(255) NULL,
    `symbol_name` VARCHAR(100) NULL,
    `manifesto` TEXT NULL,
    `status` ENUM('pending', 'approved', 'disqualified', 'withdrawn') NOT NULL DEFAULT 'approved',
    `disqualification_reason` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_candidate_election` FOREIGN KEY (`election_id`) REFERENCES `elections`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_candidate_position` FOREIGN KEY (`position_id`) REFERENCES `positions`(`id`) ON DELETE CASCADE,
    INDEX `idx_candidate_lookup` (`election_id`, `position_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 7. ELIGIBILITY RULES
-- Granular criteria defining which students can vote for a specific position.
-- ==============================================================================
CREATE TABLE `eligibility_rules` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `election_id` INT NOT NULL,
    `position_id` INT NOT NULL,
    `campus` VARCHAR(100) NOT NULL DEFAULT 'ALL' COMMENT 'ALL or specific campus name',
    `faculty` VARCHAR(150) NOT NULL DEFAULT 'ALL' COMMENT 'ALL or specific faculty name',
    `course` VARCHAR(150) NOT NULL DEFAULT 'ALL' COMMENT 'ALL or specific course name',
    `year_of_study` INT NOT NULL DEFAULT 0 COMMENT '0 means ALL years, 1-5 for specific year',
    `gender` ENUM('ALL', 'Male', 'Female') NOT NULL DEFAULT 'ALL',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_rule_election` FOREIGN KEY (`election_id`) REFERENCES `elections`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_rule_position` FOREIGN KEY (`position_id`) REFERENCES `positions`(`id`) ON DELETE CASCADE,
    INDEX `idx_rule_eval` (`election_id`, `position_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 8. TABLE A: VOTER PARTICIPATION (PREVENTS DOUBLE VOTING)
-- Tracks WHO has voted in WHICH election.
-- STRICTLY SEPARATED from ballot choices.
-- Contains a verifiable cryptographic receipt hash issued to voter.
-- ==============================================================================
CREATE TABLE `voter_participation` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `election_id` INT NOT NULL,
    `student_id` INT NOT NULL,
    `receipt_token` VARCHAR(64) NOT NULL UNIQUE COMMENT 'Cryptographic hash issued to voter as voting proof',
    `voted_at` DATETIME NOT NULL,
    `ip_address_hash` VARCHAR(64) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_part_election` FOREIGN KEY (`election_id`) REFERENCES `elections`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_part_student` FOREIGN KEY (`student_id`) REFERENCES `students`(`id`) ON DELETE CASCADE,
    CONSTRAINT `uq_student_election_vote` UNIQUE (`election_id`, `student_id`),
    INDEX `idx_participation_time` (`voted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 9. TABLE B: VOTES (ABSOLUTE ANONYMITY - ZERO VOTER LINK)
-- Stores cast ballots anonymously.
-- CRITICAL SECURITY RULE: No student_id, no user_id, no receipt_token,
-- no foreign key or join path back to the voter.
-- Records are inserted in shuffled batch order with random microsecond jitter.
-- ==============================================================================
CREATE TABLE `votes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `election_id` INT NOT NULL,
    `position_id` INT NOT NULL,
    `candidate_id` INT NULL COMMENT 'NULL represents an explicit Abstain vote',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_vote_election` FOREIGN KEY (`election_id`) REFERENCES `elections`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_vote_position` FOREIGN KEY (`position_id`) REFERENCES `positions`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_vote_candidate` FOREIGN KEY (`candidate_id`) REFERENCES `candidates`(`id`) ON DELETE SET NULL,
    INDEX `idx_tally` (`election_id`, `position_id`, `candidate_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 10. NOTIFICATIONS & ANNOUNCEMENTS
-- Official communiques, election countdown alerts, and general notices.
-- ==============================================================================
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(200) NOT NULL,
    `message` TEXT NOT NULL,
    `target_group` ENUM('all', 'students', 'admins') NOT NULL DEFAULT 'all',
    `category` ENUM('announcement', 'election_open', 'election_close', 'alert', 'results') NOT NULL DEFAULT 'announcement',
    `is_pinned` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_by` INT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_notify_admin` FOREIGN KEY (`created_by`) REFERENCES `admins`(`id`) ON DELETE SET NULL,
    INDEX `idx_notification_active` (`target_group`, `is_pinned`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 11. AUDIT LOGS
-- Immutable trail of security events, administrative adjustments, and status changes.
-- ==============================================================================
CREATE TABLE `audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_type` ENUM('student', 'admin', 'system') NOT NULL,
    `user_identifier` VARCHAR(100) NOT NULL COMMENT 'student_id or admin username (no link to vote)',
    `action` VARCHAR(100) NOT NULL COMMENT 'e.g. LOGIN, VOTE_CAST_RECORDED, CANDIDATE_APPROVED, RESULTS_PUBLISHED',
    `details` TEXT NULL,
    `ip_address` VARCHAR(50) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_audit_search` (`action`, `user_type`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 12. FREQUENTLY ASKED QUESTIONS (FAQ) & VOTER GUIDANCE
-- ==============================================================================
CREATE TABLE `faqs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `category` VARCHAR(100) NOT NULL DEFAULT 'General',
    `question` VARCHAR(255) NOT NULL,
    `answer` TEXT NOT NULL,
    `priority_order` INT NOT NULL DEFAULT 1,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
