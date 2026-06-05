ENABLED_TABLES = [
    "activity",
    "screen_event",
    "break_event_log",
    "user",
    "app_user",
    "roles",
    "app_info",
    "client",
    "tag_group",
    "tag_name",
    "tag_value",
    "tag_group_value",
    "user_tag_group",
    "user_tag_values",
    "application_category_list",
    "tagging",
    "whitelist_ip_addresses",
    "app_user_machine",
    "aux_request",
    "client_meta_data",
    ]

TENANTS = [
    "maxicus",
    "ksoft",
    "igzy"
]

TENANT_DB_MAP = {
    "maxicus":"clxyi19290000s7kvd0rrf2ho",
    "ksoft":"clyicfrro000020z5esz8uo7u",
    "igzy":"clztfag560001csuaf7o9jdgj"
}

TABLES_CONFIG = {

    # ======================
    # TIME SERIES
    # ======================

    "activity": {
        "primary_key": ["id", "capture_time"],
        "incremental_column": "capture_time",
        "strategy": "time_series"
    },

    # ======================
    # FULL REFRESH
    # ======================
  
    "screen_event": {
        "primary_key": ["id"],
        "incremental_column": "created_at",
        "strategy": "full_refresh"
    },
  
    "break_event_log": {
        "primary_key": ["id"],
        "incremental_column": "created_at",
        "strategy": "full_refresh"
    },

    "application_category_list": {
        "primary_key": ["id"],
        "incremental_column": "created_at",
        "strategy": "full_refresh"
    },
  
    "tagging": {
        "primary_key": ["id"],
        "incremental_column": "created_at",
        "strategy": "full_refresh"
    },

    "aux_request": {
        "primary_key": ["id"],
        "incremental_column": "created_at",
        "strategy": "full_refresh"
    },

    "app_user_machine": {
        "primary_key": ["id"],
        "incremental_column": "created_at",
        "strategy": "full_refresh"
    },

    "user_tag_values": {
        "primary_key": ["id"],
        "incremental_column": "created_at",
        "strategy": "full_refresh"
    },
 
    "roles": {
        "primary_key": ["id"],
        "incremental_column": "modified_at",
        "strategy": "full_refresh"
    },
  
    "app_user": {
        "primary_key": ["id"],
        "incremental_column": "updated_at",
        "strategy": "full_refresh"
    },
  
    "app_info": {
        "primary_key": ["id"],
        "incremental_column": "updated_at",
        "strategy": "full_refresh"
    },

    "whitelist_ip_addresses": {
        "primary_key": ["id"],
        "incremental_column": "updated_at",
        "strategy": "full_refresh"
    },

    "client": {
        "primary_key": ["id"],
        "incremental_column": "updated_at",
        "strategy": "full_refresh"
    },

    "client_meta_data": {
        "primary_key": ["id"],
        "incremental_column": None,
        "strategy": "full_refresh"
    },

    "tag_group": {
        "primary_key": ["id"],
        "incremental_column": None,
        "strategy": "full_refresh"
    },
  
    "tag_name": {
        "primary_key": ["id"],
        "incremental_column": None,
        "strategy": "full_refresh"
    },
  
    "tag_value": {
        "primary_key": ["id"],
        "incremental_column": None,
        "strategy": "full_refresh"
    },
  
    "tag_group_value": {
        "primary_key": ["id"],
        "incremental_column": None,
        "strategy": "full_refresh"
    },
  
    "user_tag_group": {
        "primary_key": ["user_id", "tag_group_id"],
        "incremental_column": None,
        "strategy": "full_refresh"
    },

    "user": {
        "primary_key": ["sso_id"],
        "incremental_column": "modified_at",
        "strategy": "full_refresh"
    },

}
