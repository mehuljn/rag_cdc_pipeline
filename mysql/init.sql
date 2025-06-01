-- mysql/init.sql
CREATE DATABASE IF NOT EXISTS rag_db;

USE rag_db;

CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert some initial data
INSERT INTO documents (title, content) VALUES
('The Art of War', 'Sun Tzu''s ancient Chinese military treatise.'),
('1984', 'George Orwell''s dystopian social science fiction novel.'),
('Sapiens', 'Yuval Noah Harari''s book on the history of humankind.');
