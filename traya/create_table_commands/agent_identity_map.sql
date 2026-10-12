
CREATE TABLE agent_identity_map (
    client_id   varchar(200) NOT NULL,   -- the dialer login, exactly as the dump spells it
    emp_id      varchar(50)  NOT NULL,   -- Kochar employee id. The identity. Never reissued.
    valid_from  date NOT NULL DEFAULT DATE '1900-01-01',
    valid_to    date NOT NULL DEFAULT DATE '9999-12-31',
    source      varchar(60)              -- 'seed', 'auto <date>', or who added it by hand
    PRIMARY KEY (client_id, valid_from)
)