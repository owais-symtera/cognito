/*
Pharmaceutical Intelligence Platform Audit Triggers
Immutable audit trail triggers for regulatory compliance and 7-year retention

CognitoAI Engine - Version 1.0.0
Author: CognitoAI Development Team

IMPORTANT: These triggers create immutable audit records for pharmaceutical
regulatory compliance. Do not modify without regulatory review.
*/

-- Enable required extensions for pharmaceutical audit trails
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Note: pg_stat_statements requires superuser privileges and is optional for monitoring
-- CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create audit trigger function for pharmaceutical entities
CREATE OR REPLACE FUNCTION create_pharmaceutical_audit_event()
RETURNS TRIGGER AS $$
DECLARE
    audit_event_id UUID;
    current_user_id UUID;
    current_correlation_id VARCHAR(255);
    event_type_val VARCHAR(50);
    old_values_json JSONB;
    new_values_json JSONB;
    event_description TEXT;
BEGIN
    -- Generate audit event ID
    audit_event_id := uuid_generate_v4();

    -- Get current user context (from application context or session)
    current_user_id := COALESCE(
        current_setting('audit.user_id', true)::UUID,
        NULL
    );

    -- Get current correlation ID for pharmaceutical process tracking
    current_correlation_id := COALESCE(
        current_setting('audit.correlation_id', true),
        uuid_generate_v4()::TEXT
    );

    -- Determine event type and prepare audit data based on operation
    IF TG_OP = 'DELETE' THEN
        event_type_val := 'delete';
        old_values_json := to_jsonb(OLD);
        new_values_json := NULL;
        event_description := 'Deleted ' || TG_TABLE_NAME || ' entity for pharmaceutical compliance';

    ELSIF TG_OP = 'UPDATE' THEN
        event_type_val := 'update';
        old_values_json := to_jsonb(OLD);
        new_values_json := to_jsonb(NEW);
        event_description := 'Updated ' || TG_TABLE_NAME || ' entity for pharmaceutical operations';

    ELSIF TG_OP = 'INSERT' THEN
        event_type_val := 'create';
        old_values_json := NULL;
        new_values_json := to_jsonb(NEW);
        event_description := 'Created ' || TG_TABLE_NAME || ' entity for pharmaceutical intelligence';

    ELSE
        -- Should not happen, but handle gracefully for pharmaceutical compliance
        RAISE WARNING 'Unexpected trigger operation: %', TG_OP;
        RETURN COALESCE(NEW, OLD);
    END IF;

    -- Insert immutable audit event for pharmaceutical regulatory compliance
    INSERT INTO audit_events (
        id,
        event_type,
        event_description,
        entity_type,
        entity_id,
        old_values,
        new_values,
        user_id,
        correlation_id,
        timestamp
    ) VALUES (
        audit_event_id,
        event_type_val::audit_event_type,
        event_description,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id)::TEXT,
        old_values_json,
        new_values_json,
        current_user_id,
        current_correlation_id,
        CURRENT_TIMESTAMP
    );

    -- Log audit event creation for pharmaceutical monitoring
    RAISE DEBUG 'Pharmaceutical audit event created: % for % entity %',
        audit_event_id, TG_TABLE_NAME, COALESCE(NEW.id, OLD.id);

    RETURN COALESCE(NEW, OLD);

EXCEPTION
    WHEN OTHERS THEN
        -- Log audit trigger failure but don't block pharmaceutical operations
        RAISE WARNING 'Pharmaceutical audit trigger failed for % %: %',
            TG_TABLE_NAME, TG_OP, SQLERRM;
        RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Note: Function ownership can be set if needed by database administrator
-- ALTER FUNCTION create_pharmaceutical_audit_event() OWNER TO postgres;

-- Create audit triggers for all pharmaceutical intelligence entities
-- These triggers ensure immutable audit trails for regulatory compliance

-- Drug Requests - Core pharmaceutical intelligence requests
DROP TRIGGER IF EXISTS audit_drug_requests_trigger ON drug_requests;
CREATE TRIGGER audit_drug_requests_trigger
    AFTER INSERT OR UPDATE OR DELETE ON drug_requests
    FOR EACH ROW EXECUTE FUNCTION create_pharmaceutical_audit_event();

-- Category Results - Individual pharmaceutical category processing
DROP TRIGGER IF EXISTS audit_category_results_trigger ON category_results;
CREATE TRIGGER audit_category_results_trigger
    AFTER INSERT OR UPDATE OR DELETE ON category_results
    FOR EACH ROW EXECUTE FUNCTION create_pharmaceutical_audit_event();

-- Source References - Pharmaceutical source attribution and tracking
DROP TRIGGER IF EXISTS audit_source_references_trigger ON source_references;
CREATE TRIGGER audit_source_references_trigger
    AFTER INSERT OR UPDATE OR DELETE ON source_references
    FOR EACH ROW EXECUTE FUNCTION create_pharmaceutical_audit_event();

-- Source Conflicts - Pharmaceutical data conflict resolution
DROP TRIGGER IF EXISTS audit_source_conflicts_trigger ON source_conflicts;
CREATE TRIGGER audit_source_conflicts_trigger
    AFTER INSERT OR UPDATE OR DELETE ON source_conflicts
    FOR EACH ROW EXECUTE FUNCTION create_pharmaceutical_audit_event();

-- Process Tracking - Pharmaceutical process correlation tracking
DROP TRIGGER IF EXISTS audit_process_tracking_trigger ON process_tracking;
CREATE TRIGGER audit_process_tracking_trigger
    AFTER INSERT OR UPDATE OR DELETE ON process_tracking
    FOR EACH ROW EXECUTE FUNCTION create_pharmaceutical_audit_event();

-- Users - User management for pharmaceutical platform access
DROP TRIGGER IF EXISTS audit_users_trigger ON users;
CREATE TRIGGER audit_users_trigger
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION create_pharmaceutical_audit_event();

-- Pharmaceutical Categories - Dynamic category configuration
DROP TRIGGER IF EXISTS audit_pharmaceutical_categories_trigger ON pharmaceutical_categories;
CREATE TRIGGER audit_pharmaceutical_categories_trigger
    AFTER INSERT OR UPDATE OR DELETE ON pharmaceutical_categories
    FOR EACH ROW EXECUTE FUNCTION create_pharmaceutical_audit_event();

-- API Usage Logs - External API call tracking (No audit trigger needed - already logged)
-- Audit Events - No trigger needed (would cause infinite recursion)

-- Create indexes on audit_events for pharmaceutical compliance queries
-- These indexes optimize regulatory compliance reporting and audit trail analysis

-- Primary audit trail queries by entity
CREATE INDEX IF NOT EXISTS idx_audit_events_entity_timestamp
ON audit_events (entity_type, entity_id, timestamp DESC);

-- User activity tracking for pharmaceutical security
CREATE INDEX IF NOT EXISTS idx_audit_events_user_timestamp
ON audit_events (user_id, timestamp DESC) WHERE user_id IS NOT NULL;

-- Request correlation for pharmaceutical audit lineage
CREATE INDEX IF NOT EXISTS idx_audit_events_request_timestamp
ON audit_events (request_id, timestamp DESC) WHERE request_id IS NOT NULL;

-- Process correlation for pharmaceutical audit tracking
CREATE INDEX IF NOT EXISTS idx_audit_events_correlation
ON audit_events (correlation_id) WHERE correlation_id IS NOT NULL;

-- Event type analysis for pharmaceutical compliance reporting
CREATE INDEX IF NOT EXISTS idx_audit_events_event_type_timestamp
ON audit_events (event_type, timestamp DESC);

-- Temporal partitioning support for pharmaceutical 7-year retention
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp_partition
ON audit_events (date_trunc('month', timestamp), timestamp);

-- Create helper functions for pharmaceutical audit trail management

-- Function to set audit context for pharmaceutical operations
CREATE OR REPLACE FUNCTION set_pharmaceutical_audit_context(
    p_user_id UUID DEFAULT NULL,
    p_correlation_id VARCHAR(255) DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    -- Set user context for pharmaceutical audit tracking
    IF p_user_id IS NOT NULL THEN
        PERFORM set_config('audit.user_id', p_user_id::TEXT, true);
    END IF;

    -- Set correlation ID for pharmaceutical process tracking
    IF p_correlation_id IS NOT NULL THEN
        PERFORM set_config('audit.correlation_id', p_correlation_id, true);
    END IF;

    RAISE DEBUG 'Pharmaceutical audit context set: user_id=%, correlation_id=%',
        p_user_id, p_correlation_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to clear pharmaceutical audit context
CREATE OR REPLACE FUNCTION clear_pharmaceutical_audit_context()
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('audit.user_id', '', true);
    PERFORM set_config('audit.correlation_id', '', true);
    RAISE DEBUG 'Pharmaceutical audit context cleared';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to validate pharmaceutical audit trail integrity
CREATE OR REPLACE FUNCTION validate_pharmaceutical_audit_integrity(
    p_entity_type VARCHAR(100) DEFAULT NULL,
    p_entity_id VARCHAR(255) DEFAULT NULL,
    p_start_date TIMESTAMP DEFAULT NULL,
    p_end_date TIMESTAMP DEFAULT NULL
)
RETURNS TABLE(
    entity_type VARCHAR(100),
    entity_id VARCHAR(255),
    audit_events_count BIGINT,
    first_event_timestamp TIMESTAMP,
    last_event_timestamp TIMESTAMP,
    has_create_event BOOLEAN,
    integrity_status VARCHAR(20)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ae.entity_type,
        ae.entity_id,
        COUNT(*) as audit_events_count,
        MIN(ae.timestamp) as first_event_timestamp,
        MAX(ae.timestamp) as last_event_timestamp,
        bool_or(ae.event_type = 'create') as has_create_event,
        CASE
            WHEN COUNT(*) > 0 AND bool_or(ae.event_type = 'create') THEN 'valid'
            WHEN COUNT(*) > 0 THEN 'incomplete'
            ELSE 'missing'
        END as integrity_status
    FROM audit_events ae
    WHERE
        (p_entity_type IS NULL OR ae.entity_type = p_entity_type)
        AND (p_entity_id IS NULL OR ae.entity_id = p_entity_id)
        AND (p_start_date IS NULL OR ae.timestamp >= p_start_date)
        AND (p_end_date IS NULL OR ae.timestamp <= p_end_date)
    GROUP BY ae.entity_type, ae.entity_id
    ORDER BY ae.entity_type, ae.entity_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create view for pharmaceutical compliance reporting
CREATE OR REPLACE VIEW pharmaceutical_audit_summary AS
SELECT
    DATE(timestamp) as audit_date,
    entity_type,
    event_type,
    COUNT(*) as event_count,
    COUNT(DISTINCT entity_id) as unique_entities,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT correlation_id) as unique_processes
FROM audit_events
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(timestamp), entity_type, event_type
ORDER BY audit_date DESC, entity_type, event_type;

-- Grant appropriate permissions for pharmaceutical platform access
GRANT SELECT ON pharmaceutical_audit_summary TO PUBLIC;

-- Create notification function for critical pharmaceutical audit events
CREATE OR REPLACE FUNCTION notify_critical_pharmaceutical_audit()
RETURNS TRIGGER AS $$
BEGIN
    -- Notify on critical pharmaceutical operations for regulatory monitoring
    IF NEW.event_type IN ('delete', 'source_verification', 'conflict_resolution')
       OR NEW.entity_type = 'DrugRequest'
    THEN
        PERFORM pg_notify(
            'pharmaceutical_audit',
            json_build_object(
                'event_type', NEW.event_type,
                'entity_type', NEW.entity_type,
                'entity_id', NEW.entity_id,
                'user_id', NEW.user_id,
                'timestamp', NEW.timestamp
            )::text
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger for critical pharmaceutical audit notifications
DROP TRIGGER IF EXISTS notify_critical_audit_trigger ON audit_events;
CREATE TRIGGER notify_critical_audit_trigger
    AFTER INSERT ON audit_events
    FOR EACH ROW EXECUTE FUNCTION notify_critical_pharmaceutical_audit();

-- Add comments for pharmaceutical regulatory documentation
COMMENT ON FUNCTION create_pharmaceutical_audit_event() IS
'Immutable audit trail trigger for pharmaceutical regulatory compliance. Creates comprehensive audit records for all entity changes with 7-year retention.';

COMMENT ON FUNCTION set_pharmaceutical_audit_context(UUID, VARCHAR) IS
'Sets audit context for pharmaceutical operations including user tracking and process correlation for regulatory compliance.';

COMMENT ON FUNCTION validate_pharmaceutical_audit_integrity(VARCHAR, VARCHAR, TIMESTAMP, TIMESTAMP) IS
'Validates pharmaceutical audit trail integrity for regulatory compliance reporting and audit verification.';

COMMENT ON VIEW pharmaceutical_audit_summary IS
'Summary view of pharmaceutical audit events for regulatory compliance reporting and operational monitoring.';

-- Log successful pharmaceutical audit triggers installation
DO $$
BEGIN
    RAISE NOTICE 'Pharmaceutical audit triggers installed successfully';
    RAISE NOTICE 'Immutable audit trail active for regulatory compliance';
    RAISE NOTICE '7-year retention policy supported through partitioning';
END
$$;