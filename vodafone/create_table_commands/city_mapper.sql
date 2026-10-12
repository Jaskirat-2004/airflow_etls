
CREATE TABLE city_mapper_staging (
    old_circle_code     TEXT,
    new_circle_code     TEXT
);


CREATE TABLE city_mapper (
    old_circle_code     TEXT   NOT NULL,
    new_circle_code     TEXT,
    updated_at                     TIMESTAMP DEFAULT NOW(),   -- when this row was last merged (audit/debug)
    PRIMARY KEY (old_circle_code)
);


INSERT INTO city_mapper (old_circle_code, new_circle_code) VALUES
('MAG', 'MHG'),
('PJB', 'PUN'),
('HAR', 'HAR'),
('DEL', 'DEL'),
('KAR', 'KAR'),
('UPE', 'UPE'),
('RAJ', 'RAJ'),
('AP',  'APT'),
('MUM', 'MUM'),
('ROT', 'TNC'),
('GUJ', 'GUJ'),
('UPW', 'UPW'),
('ORS', 'ODI'),
('CHN', 'TNC'),
('KOL', 'KOL'),
('ROB', 'ROB'),
('MPC', 'MPC'),
('KER', 'KER'),
('BHR', 'BHJ'),
('ASM', 'ASM'),
('JNK', 'JNK'),
('HP',  'HP'),
('NES', 'NOE');
