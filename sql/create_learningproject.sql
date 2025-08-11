-- Create database and table for the voice assistant
CREATE DATABASE IF NOT EXISTS LearningProject CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE LearningProject;

CREATE TABLE IF NOT EXISTS conversations (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_input TEXT,
  assistant_reply TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;