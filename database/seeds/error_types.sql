-- Seed data for error patterns

INSERT INTO error_patterns (id, name, description, category, examples) VALUES
    (uuid_generate_v4(), 'Letter Reversals', 'Confusing visually similar letters like b/d, p/q', 'reversal', '["b/d", "p/q", "m/w", "n/u"]'),
    (uuid_generate_v4(), 'Letter Transpositions', 'Swapping adjacent letters', 'transposition', '["teh/the", "form/from", "thier/their"]'),
    (uuid_generate_v4(), 'Phonetic Substitutions', 'Spelling based on sound rather than convention', 'phonetic', '["becuase/because", "definately/definitely"]'),
    (uuid_generate_v4(), 'Letter Omissions', 'Missing letters, especially double letters', 'omission', '["writting/writing", "occured/occurred"]'),
    (uuid_generate_v4(), 'Letter Additions', 'Extra letters added to words', 'addition', '["untill/until", "accomodate/accommodate"]'),
    (uuid_generate_v4(), 'Word Confusion', 'Mixing homophones and similar words', 'confusion', '["their/there/they''re", "your/you''re"]');
