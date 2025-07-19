CREATE TABLE scraper_tasks (
    task_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 例如: PENDING, RUNNING, COMPLETED, FAILED
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    result_summary JSONB, -- 存储成功时的统计信息
    error_details TEXT -- 存储失败时的错误信息
);
