-- Seed data for English confusion pairs

INSERT INTO confusion_pairs (id, language, word1, word2, category, frequency) VALUES
    (uuid_generate_v4(), 'en', 'their', 'there', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'their', 'they''re', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'there', 'they''re', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'your', 'you''re', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'its', 'it''s', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'to', 'too', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'to', 'two', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'too', 'two', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'then', 'than', 'similar', 0),
    (uuid_generate_v4(), 'en', 'affect', 'effect', 'similar', 0),
    (uuid_generate_v4(), 'en', 'accept', 'except', 'similar', 0),
    (uuid_generate_v4(), 'en', 'lose', 'loose', 'similar', 0),
    (uuid_generate_v4(), 'en', 'weather', 'whether', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'principal', 'principle', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'stationary', 'stationery', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'complement', 'compliment', 'homophone', 0),
    (uuid_generate_v4(), 'en', 'advice', 'advise', 'similar', 0),
    (uuid_generate_v4(), 'en', 'practice', 'practise', 'similar', 0);
