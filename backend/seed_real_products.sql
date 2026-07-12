-- Real, attractive jaggery products for the customer Category page.
-- Updates name (batch_id), grade, cover image (image_path) and a rich
-- "Ingredients / Effectiveness" description for every batch. Stock, prices and
-- harvest dates are left untouched (so the expiry/grade demos still work).
BEGIN;

UPDATE jaggery_batches SET batch_id='Premium Sugarcane Jaggery Block', grade='A', image_path='jag_real_4.jpg',
 description=E'Ingredients: 100% pure sugarcane juice, slow-boiled in iron woks — no chemicals, dyes or preservatives.\n\nEffectiveness: Naturally rich in iron and minerals; aids digestion, gently detoxifies the liver and gives steady, long-lasting energy.'
 WHERE id=1;

UPDATE jaggery_batches SET batch_id='Traditional Cane Jaggery Bheli', grade='B', image_path='jag_real_10.jpg',
 description=E'Ingredients: Pure sugarcane juice, hand-set into traditional round discs.\n\nEffectiveness: A wholesome sugar substitute that boosts haemoglobin, supports digestion and gently warms the body.'
 WHERE id=2;

UPDATE jaggery_batches SET batch_id='Organic Jaggery Powder', grade='A', image_path='jag_real_5.jpg',
 description=E'Ingredients: Certified-organic sugarcane juice, stone-ground into a fine, free-flowing powder.\n\nEffectiveness: Dissolves instantly in tea, coffee and sweets; releases energy slowly and is gentler on blood sugar than refined white sugar.'
 WHERE id=4;

UPDATE jaggery_batches SET batch_id='Palm Jaggery (Karupatti)', grade='A', image_path='jag_real_3.jpg',
 description=E'Ingredients: Pure palmyra-palm sap, traditionally reduced over a slow wood fire.\n\nEffectiveness: Low glycaemic index; rich in magnesium and potassium; soothes coughs, eases digestion and supports respiratory health.'
 WHERE id=5;

UPDATE jaggery_batches SET batch_id='Everyday Value Jaggery', grade='C', image_path='jag_real_0.jpg',
 description=E'Ingredients: Pure sugarcane jaggery in handy bite-sized pieces.\n\nEffectiveness: An affordable, all-natural sweetener for daily cooking; a great post-meal digestive and quick energy booster.'
 WHERE id=6;

UPDATE jaggery_batches SET batch_id='Coconut Palm Jaggery', grade='B', image_path='jag_real_2.jpg',
 description=E'Ingredients: Pure coconut-palm nectar, slow-cooked into golden jaggery balls.\n\nEffectiveness: Low glycaemic index and rich in amino acids, iron and zinc; nourishes the gut and provides sustained energy.'
 WHERE id=7;

UPDATE jaggery_batches SET batch_id='Farmhouse Aged Jaggery', grade='B', image_path='jag_real_8.jpg',
 description=E'Ingredients: Traditional sugarcane jaggery (a matured batch kept for the expiry demo).\n\nEffectiveness: Shows the 9-month freshness rule in action — once past harvest + 9 months it is automatically marked EXPIRED and can no longer be ordered.'
 WHERE id=8;

UPDATE jaggery_batches SET batch_id='Stone-Ground Jaggery Powder', grade='A', image_path='jag_real_5.jpg',
 description=E'Ingredients: Pure sugarcane juice, dried and milled into soft golden powder.\n\nEffectiveness: Easy to measure and quick to dissolve; a clean, mineral-rich swap for refined sugar in baking and hot drinks.'
 WHERE id=9;

UPDATE jaggery_batches SET batch_id='Golden Sugarcane Jaggery Cubes', grade='A', image_path='jag_real_0.jpg',
 description=E'Ingredients: Pure sugarcane jaggery pressed into neat, ready-to-use cubes.\n\nEffectiveness: A perfectly portioned natural sweetener; supports digestion and replenishes energy after meals or workouts.'
 WHERE id=10;

UPDATE jaggery_batches SET batch_id='Date-Palm Jaggery (Nolen Gur)', grade='A', image_path='jag_real_3.jpg',
 description=E'Ingredients: Fresh date-palm sap, slow-cooked into rich, aromatic jaggery.\n\nEffectiveness: A prized winter delicacy; high in antioxidants and iron, it strengthens immunity and lends a deep caramel flavour to sweets.'
 WHERE id=12;

UPDATE jaggery_batches SET batch_id='Ginger Jaggery (Sonth Gur)', grade='B', image_path='jag_real_2.jpg',
 description=E'Ingredients: Sugarcane jaggery blended with dried ginger.\n\nEffectiveness: A warming winter blend that soothes sore throats, relieves cold and cough and kick-starts digestion.'
 WHERE id=13;

UPDATE jaggery_batches SET batch_id='Black Jaggery (Kala Gur)', grade='C', image_path='jag_real_3.jpg',
 description=E'Ingredients: Sugarcane juice cooked low and slow until deep and dark.\n\nEffectiveness: Mineral-dense and iron-rich; helps replenish iron, supports menstrual health and naturally detoxifies the body.'
 WHERE id=15;

UPDATE jaggery_batches SET batch_id='Sesame Jaggery Bites (Til Gur)', grade='A', image_path='jag_real_0.jpg',
 description=E'Ingredients: Sugarcane jaggery with roasted sesame seeds.\n\nEffectiveness: A calcium-rich winter sweet that strengthens bones, warms the body and makes a wholesome anytime snack.'
 WHERE id=16;

UPDATE jaggery_batches SET batch_id='Marayoor Sugarcane Jaggery', grade='A', image_path='jag_real_4.jpg',
 description=E'Ingredients: GI-tagged Marayoor sugarcane juice, made entirely without chemicals.\n\nEffectiveness: Famous for its purity and high iron content; purifies the blood, relieves fatigue and aids smooth digestion.'
 WHERE id=18;

UPDATE jaggery_batches SET batch_id='Liquid Jaggery (Cane Syrup)', grade='B', image_path='jag_real_8.jpg',
 description=E'Ingredients: Concentrated sugarcane juice reduced to a smooth, pourable syrup.\n\nEffectiveness: A natural, easy-pour sweetener for drinks and desserts; soothes the throat and keeps digestion comfortable.'
 WHERE id=20;

UPDATE jaggery_batches SET batch_id='Turmeric Jaggery (Haldi Gur)', grade='A', image_path='jag_real_5.jpg',
 description=E'Ingredients: Sugarcane jaggery infused with pure turmeric.\n\nEffectiveness: An anti-inflammatory golden blend that boosts immunity, supports the joints and promotes clear, healthy skin.'
 WHERE id=27;

UPDATE jaggery_batches SET batch_id='Cardamom Jaggery (Elaichi Gur)', grade='A', image_path='jag_real_2.jpg',
 description=E'Ingredients: Sugarcane jaggery scented with green cardamom.\n\nEffectiveness: A fragrant after-meal sweet that freshens breath, calms the stomach and helps ease bloating.'
 WHERE id=28;

UPDATE jaggery_batches SET batch_id='Artisan Jaggery Gift Box', grade='A', image_path='jag_real_0.jpg',
 description=E'Ingredients: A hand-picked assortment of pure sugarcane and palm jaggery — blocks, balls and cubes.\n\nEffectiveness: A wholesome gift of natural sweetness — iron-rich, chemical-free and perfect for festivals and hampers.'
 WHERE id=31;

UPDATE jaggery_batches SET batch_id='Fennel Jaggery (Saunf Gur)', grade='B', image_path='jag_real_10.jpg',
 description=E'Ingredients: Sugarcane jaggery mixed with roasted fennel seeds.\n\nEffectiveness: The classic after-meal digestive; reduces bloating and acidity and naturally freshens the mouth.'
 WHERE id=34;

-- Refresh the "Artisan Jaggery Gift Box" gallery with real photos (📷 multi-image demo)
DELETE FROM batch_images WHERE batch_id=31;
INSERT INTO batch_images (batch_id, image_path) VALUES
 (31,'jag_real_2.jpg'), (31,'jag_real_4.jpg'), (31,'jag_real_10.jpg');

-- Give the Premium block a small 2-photo gallery too
INSERT INTO batch_images (batch_id, image_path) VALUES (1,'jag_real_8.jpg');

COMMIT;
