--
-- PostgreSQL database dump
--

\restrict 1WrSnMNvvwq436iPb4fY0ffijswNOXv0KIJ3x9xrCWYIqyHojWXfGuZGtyLbIr4

-- Dumped from database version 15.16 (Debian 15.16-1.pgdg13+1)
-- Dumped by pg_dump version 15.16 (Debian 15.16-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

SET SESSION AUTHORIZATION DEFAULT;

ALTER TABLE public.users DISABLE TRIGGER ALL;

COPY public.users (id, nickname, username, primary_email, password_hash, primary_phone, points, avatar, role, created_at, is_active, openid, github_id) FROM stdin;
8a04e64a-4729-4c34-a450-fb019fa4a428	DemoUserA	demo_user_a	demo_user_a@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.655832	t	\N	\N
d50230e7-915a-4135-bc48-c5fa84b5f422	DemoAdmin	demo_admin	demo_admin@example.com	\N	\N	10000	\N	admin	2026-02-15 17:36:06.624308	t	\N	\N
232584d9-4cc5-455f-8d8c-c2f30382dcee	DemoDev	demo_dev	demo_dev@example.com	\N	\N	5000	\N	student	2026-02-15 17:36:06.628133	t	\N	\N
f9b1b6f3-6880-4955-a671-495c5bf8cc3b	DemoUser01	demo_user_01	demo_user_01@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.629618	t	\N	\N
e753cd4f-b43b-4b5a-a5f6-a6ebbf14a6e3	DemoUser02	demo_user_02	demo_user_02@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.631006	t	\N	\N
9551db69-883a-4ce3-b7a9-fec54c0e11aa	DemoUser03	demo_user_03	demo_user_03@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.632448	t	\N	\N
09ed1a7c-69c1-46b7-a66b-95a864a3895d	DemoUser04	demo_user_04	demo_user_04@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.633784	t	\N	\N
c1f03328-a33e-4df5-8873-34ede35d225e	DemoUser05	demo_user_05	demo_user_05@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.635297	t	\N	\N
e739ac4d-0b0a-4bf4-ba44-e0d33d8bf51d	DemoUser06	demo_user_06	demo_user_06@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.636762	t	\N	\N
950d740e-9aca-431b-ada1-74a4fe41cc86	DemoUser07	demo_user_07	demo_user_07@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.638178	t	\N	\N
dce70900-6fc8-4835-ad71-b192af691bde	DemoUser08	demo_user_08	demo_user_08@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.63959	t	\N	\N
b096eaf0-e50d-42d7-8d58-88c4c7c6a053	DemoUser09	demo_user_09	demo_user_09@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.640954	t	\N	\N
58e3239b-0406-4aa8-8d81-cec5e3b9c7cc	DemoUser10	demo_user_10	demo_user_10@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.642362	t	\N	\N
a7c07ced-1717-41a4-9d42-a467bcb7402c	DemoUser11	demo_user_11	demo_user_11@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.643873	t	\N	\N
2975a50c-98de-437a-9053-f423296af4be	DemoUser12	demo_user_12	demo_user_12@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.645242	t	\N	\N
65c1b514-0b9f-46b5-b4dc-d722f9f47927	DemoUser13	demo_user_13	demo_user_13@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.646627	t	\N	\N
a219a456-978a-4231-92aa-c9613e4243c0	DemoUser14	demo_user_14	demo_user_14@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.648105	t	\N	\N
45b7557a-8b06-4cf1-a938-c3959ed27916	DemoUser15	demo_user_15	demo_user_15@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.649605	t	\N	\N
f0cf6463-73e9-42c2-82f6-fed85a7ef111	DemoUser16	demo_user_16	demo_user_16@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.651028	t	\N	\N
0f945309-e71e-4529-b0d2-c72e344b72d2	DemoUser17	demo_user_17	demo_user_17@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.652486	t	\N	\N
758b60f1-4e4f-4856-83b4-d45134276d99	DemoUser20	demo_user_20	demo_user_20@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.657195	t	\N	\N
a2279e3c-c0ab-4120-80ea-269b06075356	DemoUser18	demo_user_18	demo_user_18@example.com	\N	\N	1000	\N	student	2026-02-15 17:36:06.65423	t	\N	\N
\.


ALTER TABLE public.users ENABLE TRIGGER ALL;

--
-- Data for Name: assets; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.assets DISABLE TRIGGER ALL;

COPY public.assets (id, author_id, image_url, model_url, prompt, base_model, seed, steps, sampler, tags, stats, is_published, created_at) FROM stdin;
b34e775f-1a10-4489-8840-c31414cb72a3	d50230e7-915a-4135-bc48-c5fa84b5f422	https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800&h=600&fit=crop&q=80	https://example.com/model/demo-catgirl.stl	赛博猫娘，发光护目镜，赛博朋克风格，Q版	clay	\N	\N	\N	["CYBER", "Q-Version"]	{"likes": 450, "downloads": 1204}	t	2026-02-15 17:36:06.663216
2c5f1e6a-40a8-430e-9288-89923f64cc91	d50230e7-915a-4135-bc48-c5fa84b5f422	https://api.dicebear.com/7.x/bottts/svg?seed=Robot	https://example.com/model/demo-elder.stl	智慧长老，硬表面建模，细节丰富	mecha	\N	\N	\N	["HARD-SURFACE"]	{"likes": 233, "downloads": 802}	t	2026-02-15 17:36:06.663216
4b3c42ef-3485-43d7-bef6-0fc6220f9816	d50230e7-915a-4135-bc48-c5fa84b5f422	https://example.com/assets/demo-dog-preview.png	https://example.com/assets/demo-dog-model.glb	一只穿着宇航服的柴犬，4k画质	hunyuan-3d	12345	20	euler_a	[]	{"likes": 0, "downloads": 0}	t	2026-02-21 09:27:43.321738
\.


ALTER TABLE public.assets ENABLE TRIGGER ALL;

--
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.categories DISABLE TRIGGER ALL;

COPY public.categories (id, name, parent_id, description, icon, sort_order, is_active, created_at) FROM stdin;
11111111-1111-1111-1111-111111111111	Hardware	\N	AI smart base and printers	cpu	1	t	2026-02-22 05:46:20.730204
22222222-2222-2222-2222-222222222222	Materials	\N	PLA and ABS printing materials	box	2	t	2026-02-22 05:46:20.730204
33333333-3333-3333-3333-333333333333	Print Service	\N	Custom 3D printing service	printer	3	t	2026-02-22 05:46:20.730204
\.


ALTER TABLE public.categories ENABLE TRIGGER ALL;

--
-- Data for Name: courses; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.courses DISABLE TRIGGER ALL;

COPY public.courses (id, title, description, level, price, duration_hours, content, is_active, created_at) FROM stdin;
50c25a82-e194-4dc4-9f6e-8d24ff83ef7e	L1 启蒙：AI造物主	学习基础提示词，生成平面浮雕，体验3D打印乐趣。	L1	499.00	6	{}	t	2026-02-15 17:36:06.659852
5c1ad721-3e83-4bed-8781-de1baee5948e	L2 进阶：赋予手办“灵魂”	AI辅助建模 + 实体化 + 智能底座，项目制学习。	L2	1499.00	10	{}	t	2026-02-15 17:36:06.659852
0ae79527-baff-4715-8dac-87a62fa8211c	L3 高阶：实训就业	参与真实项目实训，完成作品集，衔接就业路径。	L3	2499.00	16	{}	t	2026-02-15 17:36:06.659852
\.


ALTER TABLE public.courses ENABLE TRIGGER ALL;

--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.products DISABLE TRIGGER ALL;

COPY public.products (id, name, description, category_id, price, price_type, price_unit, stock, stock_type, images, specs, status, sort_order, created_at, updated_at) FROM stdin;
44444444-4444-4444-4444-444444444444	AI 智能底座 (The Soul)	智能通用底座，支持语音交互和AI对话功能。可更换手办，实现不同角色的智能陪伴。	11111111-1111-1111-1111-111111111111	299.00	fixed	元/件	100	limited	["/images/products/base-soul.png"]	{"size": "10cm x 10cm", "color": "白色", "weight": "500g", "features": ["语音交互", "AI对话", "可更换手办"]}	active	1	2026-02-22 05:46:20.734363	2026-02-22 05:46:20.734363
66666666-6666-6666-6666-666666666666	PLA 耗材（按克重计价）	购买 PLA 耗材，按克重计价（2元/g），用于日常打印与课堂备料。	22222222-2222-2222-2222-222222222222	0.00	weight	元/g	50000	limited	["/images/products/material-pla.png"]	{"colors": ["白色", "黑色", "红色", "蓝色"], "package": "1kg/卷", "material": "PLA", "price_per_gram": 2.00}	active	2	2026-02-22 05:46:20.734363	2026-02-22 05:46:20.734363
\.


ALTER TABLE public.products ENABLE TRIGGER ALL;

--
-- Data for Name: user_identities; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.user_identities DISABLE TRIGGER ALL;

COPY public.user_identities (id, user_id, provider, identifier, credential, linked_at, credits_contributed) FROM stdin;
5a7f5664-355a-425a-885c-ba553a666f54	8a04e64a-4729-4c34-a450-fb019fa4a428	account	demo_user_a	{}	2026-02-22 05:50:43.66143	0
ac64292f-a29e-4f5a-b3f0-77e9df8761a3	d50230e7-915a-4135-bc48-c5fa84b5f422	account	demo_admin	{}	2026-02-22 05:50:43.66143	0
09c05fc4-ebb5-4e4b-a721-c5bbb9e7de35	232584d9-4cc5-455f-8d8c-c2f30382dcee	account	demo_dev	{}	2026-02-22 05:50:43.66143	0
1e56b4f8-7a0b-49ec-997d-f8777ceebd7c	f9b1b6f3-6880-4955-a671-495c5bf8cc3b	account	demo_user_01	{}	2026-02-22 05:50:43.66143	0
199ea537-460b-456a-b573-1061c9164217	e753cd4f-b43b-4b5a-a5f6-a6ebbf14a6e3	account	demo_user_02	{}	2026-02-22 05:50:43.66143	0
247f2099-03b6-4878-84b4-52f0dd4c159c	9551db69-883a-4ce3-b7a9-fec54c0e11aa	account	demo_user_03	{}	2026-02-22 05:50:43.66143	0
82650a21-8906-4afb-9fe4-fec1eab7fbce	09ed1a7c-69c1-46b7-a66b-95a864a3895d	account	demo_user_04	{}	2026-02-22 05:50:43.66143	0
c839c152-e22c-49a5-b69e-6d8786cde385	c1f03328-a33e-4df5-8873-34ede35d225e	account	demo_user_05	{}	2026-02-22 05:50:43.66143	0
a683935b-ee5a-4467-b922-d809df4e13bd	e739ac4d-0b0a-4bf4-ba44-e0d33d8bf51d	account	demo_user_06	{}	2026-02-22 05:50:43.66143	0
e716981f-d644-49d7-b28b-b0276e08e92f	950d740e-9aca-431b-ada1-74a4fe41cc86	account	demo_user_07	{}	2026-02-22 05:50:43.66143	0
a0fcefdd-a405-436a-80b8-3d4f2a7ea18a	dce70900-6fc8-4835-ad71-b192af691bde	account	demo_user_08	{}	2026-02-22 05:50:43.66143	0
e7ddfffa-8f87-4aa5-baf1-c2ed68becbb9	b096eaf0-e50d-42d7-8d58-88c4c7c6a053	account	demo_user_09	{}	2026-02-22 05:50:43.66143	0
4549751c-b971-4e29-be61-e328b3ca3486	58e3239b-0406-4aa8-8d81-cec5e3b9c7cc	account	demo_user_10	{}	2026-02-22 05:50:43.66143	0
187f4394-17c2-4d55-83b5-94af9a1bf49c	a7c07ced-1717-41a4-9d42-a467bcb7402c	account	demo_user_11	{}	2026-02-22 05:50:43.66143	0
d7818766-2735-4b34-a1ae-bae4e91511fa	2975a50c-98de-437a-9053-f423296af4be	account	demo_user_12	{}	2026-02-22 05:50:43.66143	0
a3663428-754f-47af-af68-3c325b32adb1	65c1b514-0b9f-46b5-b4dc-d722f9f47927	account	demo_user_13	{}	2026-02-22 05:50:43.66143	0
652ca70f-766a-4d30-a589-eb530ee3606c	a219a456-978a-4231-92aa-c9613e4243c0	account	demo_user_14	{}	2026-02-22 05:50:43.66143	0
6813b0c4-940d-4370-8dbf-5868918f0261	45b7557a-8b06-4cf1-a938-c3959ed27916	account	demo_user_15	{}	2026-02-22 05:50:43.66143	0
a044328d-750f-44da-aa2e-138ae8f27ce9	f0cf6463-73e9-42c2-82f6-fed85a7ef111	account	demo_user_16	{}	2026-02-22 05:50:43.66143	0
eceac774-ee9b-4270-8744-587bce84e5ce	0f945309-e71e-4529-b0d2-c72e344b72d2	account	demo_user_17	{}	2026-02-22 05:50:43.66143	0
8d2346d3-bf53-4b64-92f1-69248b2683f1	758b60f1-4e4f-4856-83b4-d45134276d99	account	demo_user_20	{}	2026-02-22 05:50:43.66143	0
e3f993e0-df09-48cd-a1a1-f4bd16edb7a3	a2279e3c-c0ab-4120-80ea-269b06075356	account	demo_user_18	{}	2026-02-22 05:50:43.66143	0
\.


ALTER TABLE public.user_identities ENABLE TRIGGER ALL;

--
-- PostgreSQL database dump complete
--

\unrestrict 1WrSnMNvvwq436iPb4fY0ffijswNOXv0KIJ3x9xrCWYIqyHojWXfGuZGtyLbIr4



-- ============================================
-- Migrations Data
-- ============================================

-- Source: 001_add_mall_tables.sql (Data)


-- 插入商品分类
INSERT INTO categories (id, name, description, icon, sort_order) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Hardware', 'AI smart base and printers', 'cpu', 1),
    ('22222222-2222-2222-2222-222222222222', 'Materials', 'PLA and ABS printing materials', 'box', 2),
    ('33333333-3333-3333-3333-333333333333', 'Print Service', 'Custom 3D printing service', 'printer', 3)
ON CONFLICT (id) DO NOTHING;

-- 插入商品数据（迁移现有3个商品）
INSERT INTO products (id, name, description, category_id, price, price_type, price_unit, stock, stock_type, images, specs, status, sort_order) VALUES
    (
        '44444444-4444-4444-4444-444444444444',
        'AI 智能底座 (The Soul)',
        '智能通用底座，支持语音交互和AI对话功能。可更换手办，实现不同角色的智能陪伴。',
        '11111111-1111-1111-1111-111111111111',
        299.00,
        'fixed',
        '元/件',
        100,
        'limited',
        '["/images/products/base-soul.png"]'::jsonb,
        '{"color": "白色", "size": "10cm x 10cm", "weight": "500g", "features": ["语音交互", "AI对话", "可更换手办"]}'::jsonb,
        'active',
        1
    ),
    (
        '66666666-6666-6666-6666-666666666666',
        'PLA 耗材（按克重计价）',
        '购买 PLA 耗材，按克重计价（2元/g），用于日常打印与课堂备料。',
        '22222222-2222-2222-2222-222222222222',
        0,
        'weight',
        '元/g',
        50000,
        'limited',
        '["/images/products/material-pla.png"]'::jsonb,
        '{"material": "PLA", "price_per_gram": 2.00, "colors": ["白色", "黑色", "红色", "蓝色"], "package": "1kg/卷"}'::jsonb,
        'active',
        2
    )
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 完成提示
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '✅ 商城模块数据库迁移完成！';
    RAISE NOTICE '   - 已创建 5 张表: categories, products, order_items, print_orders, carts';
    RAISE NOTICE '   - 已初始化 3 个商品分类';
    RAISE NOTICE '   - 已迁移 3 个商品数据';
END $$;

-- Source: 002_insert_initial_data.sql
-- ============================================
-- Insert initial mall data
-- Version: v1.0
-- Date: 2026-02-20
-- ============================================

-- Insert categories
INSERT INTO categories (id, name, description, icon, sort_order) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Hardware', 'AI smart base and printers', 'cpu', 1),
    ('22222222-2222-2222-2222-222222222222', 'Materials', 'PLA and ABS printing materials', 'box', 2),
    ('33333333-3333-3333-3333-333333333333', 'Print Service', 'Custom 3D printing service', 'printer', 3)
ON CONFLICT (id) DO NOTHING;

-- Insert products (定制白模已永久删除)
INSERT INTO products (id, name, description, category_id, price, price_type, price_unit, stock, stock_type, images, specs, status, sort_order) VALUES
    (
        '44444444-4444-4444-4444-444444444444',
        'AI Smart Base (The Soul)',
        'Smart universal base with voice interaction and AI dialogue. Replaceable figurines for different character companions.',
        '11111111-1111-1111-1111-111111111111',
        299.00,
        'fixed',
        'CNY/unit',
        100,
        'limited',
        '["/images/products/base-soul.png"]'::jsonb,
        '{"color": "White", "size": "10cm x 10cm", "weight": "500g", "features": ["Voice Interaction", "AI Dialogue", "Replaceable Figurines"]}'::jsonb,
        'active',
        1
    ),
    (
        '66666666-6666-6666-6666-666666666666',
        'PLA Filament (Priced by Weight)',
        'Purchase PLA filament, priced by weight (2 CNY/g), for daily printing and classroom supplies.',
        '22222222-2222-2222-2222-222222222222',
        0,
        'weight',
        'CNY/g',
        50000,
        'limited',
        '["/images/products/material-pla.png"]'::jsonb,
        '{"material": "PLA", "price_per_gram": 2.00, "colors": ["White", "Black", "Red", "Blue"], "package": "1kg/roll"}'::jsonb,
        'active',
        2
    )
ON CONFLICT (id) DO NOTHING;

-- Verify data
SELECT 'Categories inserted: ' || COUNT(*) FROM categories;
SELECT 'Products inserted: ' || COUNT(*) FROM products;

-- Source: 005_add_recharge_tiers.sql (Data)
-- 插入默认充值档位
INSERT INTO recharge_tiers (min_amount, bonus_rate, bonus_fixed, description, sort_order) VALUES
(100, 0, 0, '充值100积分', 1),
(500, 5, 0, '充值500积分，赠送5%', 2),
(1000, 10, 0, '充值1000积分，赠送10%', 3),
(5000, 15, 0, '充值5000积分，赠送15%', 4),
(10000, 20, 0, '充值10000积分，赠送20%', 5);

-- 添加注释
COMMENT ON TABLE recharge_tiers IS '充值档位配置表';
COMMENT ON COLUMN recharge_tiers.min_amount IS '最低充值积分数';
COMMENT ON COLUMN recharge_tiers.bonus_rate IS '赠送比例（百分比）';
COMMENT ON COLUMN recharge_tiers.bonus_fixed IS '固定赠送积分数';
COMMENT ON COLUMN recharge_tiers.description IS '档位描述';

