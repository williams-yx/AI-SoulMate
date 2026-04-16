--
-- PostgreSQL database dump
--


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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: addresses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.addresses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    name character varying(50) NOT NULL,
    phone character varying(20) NOT NULL,
    province character varying(50) NOT NULL,
    city character varying(50) NOT NULL,
    district character varying(50) NOT NULL,
    address text NOT NULL,
    is_default boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.addresses OWNER TO postgres;

--
-- Name: assets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.assets (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    author_id uuid,
    image_url text NOT NULL,
    model_url text NOT NULL,
    prompt text NOT NULL,
    base_model character varying(50) NOT NULL,
    seed integer,
    steps integer,
    sampler character varying(50),
    tags jsonb DEFAULT '[]'::jsonb,
    stats jsonb DEFAULT '{"likes": 0, "downloads": 0}'::jsonb,
    is_published boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.assets OWNER TO postgres;

--
-- Name: carts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.carts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    product_id uuid NOT NULL,
    quantity integer DEFAULT 1 NOT NULL,
    specs jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.carts OWNER TO postgres;

--
-- Name: categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.categories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL,
    parent_id uuid,
    description text,
    icon character varying(100),
    sort_order integer DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.categories OWNER TO postgres;

--
-- Name: courses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.courses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    level character varying(10) NOT NULL,
    price numeric(10,2) NOT NULL,
    duration_hours integer NOT NULL,
    content jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.courses OWNER TO postgres;

--
-- Name: devices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    device_id character varying(100) NOT NULL,
    char_prompt text,
    last_sync_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.devices OWNER TO postgres;

--
-- Name: operation_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operation_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    admin_id uuid,
    action character varying(50) NOT NULL,
    resource_type character varying(50) NOT NULL,
    resource_id uuid,
    details jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.operation_logs OWNER TO postgres;

--
-- Name: order_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.order_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    product_id uuid,
    product_type character varying(50) DEFAULT 'product'::character varying,
    product_snapshot jsonb NOT NULL,
    quantity integer DEFAULT 1 NOT NULL,
    unit_price numeric(10,2) NOT NULL,
    total_price numeric(10,2) NOT NULL,
    specs jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.order_items OWNER TO postgres;

--
-- Name: orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.orders (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    items jsonb NOT NULL,
    total_amount numeric(10,2) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    address_id uuid,
    payment_method character varying(50),
    shipping_address jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    payment_id character varying(255)
);


ALTER TABLE public.orders OWNER TO postgres;

--
-- Name: print_jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.print_jobs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    asset_id uuid,
    image_url text,
    prompt text,
    status character varying(20) DEFAULT 'pending'::character varying,
    credits_used integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.print_jobs OWNER TO postgres;

--
-- Name: print_orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.print_orders (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    print_job_id uuid NOT NULL,
    asset_id uuid NOT NULL,
    print_specs jsonb,
    estimated_weight numeric(10,2),
    actual_weight numeric(10,2),
    price_per_gram numeric(10,2) DEFAULT 2.00,
    shipping_company character varying(100),
    tracking_number character varying(100),
    shipped_at timestamp without time zone,
    received_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.print_orders OWNER TO postgres;

--
-- Name: products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.products (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    category_id uuid,
    price numeric(10,2) DEFAULT 0 NOT NULL,
    price_type character varying(20) DEFAULT 'fixed'::character varying,
    price_unit character varying(20),
    stock integer DEFAULT 0,
    stock_type character varying(20) DEFAULT 'limited'::character varying,
    images jsonb DEFAULT '[]'::jsonb,
    specs jsonb DEFAULT '{}'::jsonb,
    status character varying(20) DEFAULT 'active'::character varying,
    sort_order integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.products OWNER TO postgres;

--
-- Name: projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    title character varying(200) NOT NULL,
    description text,
    prompt text NOT NULL,
    style_model character varying(50) NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying,
    model_url text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.projects OWNER TO postgres;

--
-- Name: user_courses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_courses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    course_id uuid,
    enrolled_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    progress integer DEFAULT 0
);


ALTER TABLE public.user_courses OWNER TO postgres;

--
-- Name: user_identities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_identities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    provider character varying(50) NOT NULL,
    identifier character varying(255) NOT NULL,
    credential jsonb DEFAULT '{}'::jsonb,
    linked_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    credits_contributed integer DEFAULT 0 NOT NULL,
    free_contributed integer DEFAULT 0 NOT NULL,
    paid_contributed integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.user_identities OWNER TO postgres;

--
-- Name: user_model_configs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_model_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    name character varying(100) NOT NULL,
    api_endpoint text NOT NULL,
    api_key text,
    auth_type character varying(50) DEFAULT 'api_key'::character varying,
    model_name character varying(100),
    provider character varying(50),
    parameters jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    is_default boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.user_model_configs OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nickname character varying(50) NOT NULL,
    username character varying(50),
    primary_email character varying(100),
    password_hash character varying(255),
    primary_phone character varying(20),
    points integer DEFAULT 100,
    avatar text,
    role character varying(20) DEFAULT 'student'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_active boolean DEFAULT true,
    openid character varying(100),
    github_id character varying(100)
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: workflow_executions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workflow_executions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workflow_id uuid,
    user_id uuid,
    status character varying(20) DEFAULT 'running'::character varying,
    input_data jsonb,
    output_data jsonb,
    execution_log jsonb,
    error_message text,
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone
);


ALTER TABLE public.workflow_executions OWNER TO postgres;

--
-- Name: workflows; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workflows (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    creator_id uuid,
    graph_data jsonb NOT NULL,
    is_published boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description text,
    version integer DEFAULT 1,
    tags jsonb DEFAULT '[]'::jsonb,
    execution_count integer DEFAULT 0,
    last_executed_at timestamp without time zone
);


ALTER TABLE public.workflows OWNER TO postgres;

--
-- Name: asset_likes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asset_likes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    asset_id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.asset_likes OWNER TO postgres;

--
-- Name: asset_downloads; Type: TABLE; Schema: public; Owner: postgres
-- 说明：用于下载去重统计，每个用户对同一作品只计一次下载
--

CREATE TABLE public.asset_downloads (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    asset_id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.asset_downloads OWNER TO postgres;

--
-- Name: comments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.comments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    asset_id uuid NOT NULL,
    author_id uuid,
    parent_id uuid,
    content text NOT NULL,
    images jsonb DEFAULT '[]'::jsonb,
    videos jsonb DEFAULT '[]'::jsonb,
    like_count integer DEFAULT 0,
    reply_count integer DEFAULT 0,
    status character varying(20) DEFAULT 'published'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.comments OWNER TO postgres;

--
-- Name: comment_likes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.comment_likes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    comment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.comment_likes OWNER TO postgres;

--
-- Name: studio_history; Type: TABLE; Schema: public; Owner: postgres
--
CREATE TABLE public.studio_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    mode character varying(20) NOT NULL,
    prompt text,
    params jsonb DEFAULT '{}'::jsonb,
    preview_url text,
    asset_id uuid,
    created_at timestamp with time zone DEFAULT now()
);
ALTER TABLE public.studio_history OWNER TO postgres;

--
-- Name: studio_jobs; Type: TABLE; Schema: public; Owner: postgres
--
CREATE TABLE public.studio_jobs (
    job_id text NOT NULL,
    user_id uuid NOT NULL,
    mode character varying(20) NOT NULL,
    prompt text,
    base_model text,
    with_texture boolean DEFAULT true,
    generation_params jsonb DEFAULT '{}'::jsonb,
    param_notes jsonb,
    credits_used integer DEFAULT 0,
    charged_at timestamp with time zone,
    asset_id uuid,
    created_at timestamp with time zone DEFAULT now()
);
ALTER TABLE public.studio_jobs OWNER TO postgres;

--
-- Name: addresses addresses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.addresses
    ADD CONSTRAINT addresses_pkey PRIMARY KEY (id);


--
-- Name: assets assets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_pkey PRIMARY KEY (id);


--
-- Name: carts carts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT carts_pkey PRIMARY KEY (id);


--
-- Name: carts carts_user_id_product_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT carts_user_id_product_id_key UNIQUE (user_id, product_id);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (id);


--
-- Name: devices devices_device_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_device_id_key UNIQUE (device_id);


--
-- Name: devices devices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (id);


--
-- Name: operation_logs operation_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operation_logs
    ADD CONSTRAINT operation_logs_pkey PRIMARY KEY (id);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: print_jobs print_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.print_jobs
    ADD CONSTRAINT print_jobs_pkey PRIMARY KEY (id);


--
-- Name: print_orders print_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.print_orders
    ADD CONSTRAINT print_orders_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: user_courses user_courses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_courses
    ADD CONSTRAINT user_courses_pkey PRIMARY KEY (id);


--
-- Name: user_courses user_courses_user_id_course_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_courses
    ADD CONSTRAINT user_courses_user_id_course_id_key UNIQUE (user_id, course_id);


--
-- Name: user_identities user_identities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_identities
    ADD CONSTRAINT user_identities_pkey PRIMARY KEY (id);


--
-- Name: user_identities user_identities_provider_identifier_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_identities
    ADD CONSTRAINT user_identities_provider_identifier_key UNIQUE (provider, identifier);


--
-- Name: user_identities user_identities_user_id_provider_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_identities
    ADD CONSTRAINT user_identities_user_id_provider_key UNIQUE (user_id, provider);


--
-- Name: user_model_configs user_model_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_model_configs
    ADD CONSTRAINT user_model_configs_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (primary_email);


--
-- Name: users users_github_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_github_id_key UNIQUE (github_id);


--
-- Name: users users_openid_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_openid_key UNIQUE (openid);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (nickname);


--
-- Name: workflow_executions workflow_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_executions
    ADD CONSTRAINT workflow_executions_pkey PRIMARY KEY (id);


--
-- Name: workflows workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflows
    ADD CONSTRAINT workflows_pkey PRIMARY KEY (id);

--
-- Name: users users_username_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_unique UNIQUE (username);

--
-- Name: asset_likes asset_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.asset_likes
    ADD CONSTRAINT asset_likes_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.asset_likes
    ADD CONSTRAINT asset_likes_asset_id_user_id_key UNIQUE (asset_id, user_id);

--
-- Name: asset_downloads asset_downloads_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.asset_downloads
    ADD CONSTRAINT asset_downloads_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.asset_downloads
    ADD CONSTRAINT asset_downloads_asset_id_user_id_key UNIQUE (asset_id, user_id);

--
-- Name: comments comments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_pkey PRIMARY KEY (id);

--
-- Name: comment_likes comment_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.comment_likes
    ADD CONSTRAINT comment_likes_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.comment_likes
    ADD CONSTRAINT comment_likes_comment_id_user_id_key UNIQUE (comment_id, user_id);

--
-- Name: studio_history studio_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.studio_history
    ADD CONSTRAINT studio_history_pkey PRIMARY KEY (id);

--
-- Name: studio_jobs studio_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.studio_jobs
    ADD CONSTRAINT studio_jobs_pkey PRIMARY KEY (job_id);


--
-- Name: idx_assets_author; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_assets_author ON public.assets USING btree (author_id);


--
-- Name: idx_assets_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_assets_created ON public.assets USING btree (created_at);


--
-- Name: idx_assets_published; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_assets_published ON public.assets USING btree (is_published);


--
-- Name: idx_carts_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_carts_product ON public.carts USING btree (product_id);


--
-- Name: idx_carts_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_carts_user ON public.carts USING btree (user_id);


--
-- Name: idx_categories_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_categories_active ON public.categories USING btree (is_active);


--
-- Name: idx_categories_parent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_categories_parent ON public.categories USING btree (parent_id);


--
-- Name: idx_order_items_order; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_order_items_order ON public.order_items USING btree (order_id);


--
-- Name: idx_order_items_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_order_items_product ON public.order_items USING btree (product_id);


--
-- Name: idx_orders_payment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_orders_payment_id ON public.orders USING btree (payment_id);


--
-- Name: idx_print_orders_asset; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_print_orders_asset ON public.print_orders USING btree (asset_id);


--
-- Name: idx_print_orders_job; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_print_orders_job ON public.print_orders USING btree (print_job_id);


--
-- Name: idx_print_orders_order; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_print_orders_order ON public.print_orders USING btree (order_id);


--
-- Name: idx_products_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_category ON public.products USING btree (category_id);


--
-- Name: idx_products_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_created ON public.products USING btree (created_at DESC);


--
-- Name: idx_products_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_status ON public.products USING btree (status);


--
-- Name: idx_user_identities_provider_identifier; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_identities_provider_identifier ON public.user_identities USING btree (provider, identifier);


--
-- Name: idx_user_identities_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_identities_user_id ON public.user_identities USING btree (user_id);


--
-- Name: idx_user_model_configs_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_model_configs_active ON public.user_model_configs USING btree (user_id, is_active);


--
-- Name: idx_user_model_configs_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_model_configs_user ON public.user_model_configs USING btree (user_id);


--
-- Name: idx_workflow_executions_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_workflow_executions_user ON public.workflow_executions USING btree (user_id);


--
-- Name: idx_workflow_executions_workflow; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_workflow_executions_workflow ON public.workflow_executions USING btree (workflow_id);


--
-- Indexes for community features
--

CREATE INDEX idx_asset_likes_asset ON public.asset_likes USING btree (asset_id);
CREATE INDEX idx_asset_likes_user ON public.asset_likes USING btree (user_id);

CREATE INDEX idx_asset_downloads_asset ON public.asset_downloads USING btree (asset_id);
CREATE INDEX idx_asset_downloads_user ON public.asset_downloads USING btree (user_id);

CREATE INDEX idx_comments_asset ON public.comments USING btree (asset_id);
CREATE INDEX idx_comments_author ON public.comments USING btree (author_id);

CREATE INDEX idx_comment_likes_comment ON public.comment_likes USING btree (comment_id);
CREATE INDEX idx_comment_likes_user ON public.comment_likes USING btree (user_id);

CREATE INDEX idx_studio_history_user_created ON public.studio_history USING btree (user_id, created_at DESC);
CREATE INDEX idx_studio_jobs_asset_null ON public.studio_jobs USING btree (created_at) WHERE (asset_id IS NULL);


--
-- Name: addresses addresses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.addresses
    ADD CONSTRAINT addresses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: assets assets_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id);


--
-- Name: carts carts_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT carts_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: carts carts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT carts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: categories categories_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.categories(id) ON DELETE SET NULL;


--
-- Name: devices devices_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: operation_logs operation_logs_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operation_logs
    ADD CONSTRAINT operation_logs_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.users(id);


--
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_items order_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE SET NULL;


--
-- Name: orders orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: print_jobs print_jobs_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
-- 说明：删除作品时不再阻塞已有打印任务，asset_id 置为 NULL 以保留任务记录
--

ALTER TABLE ONLY public.print_jobs
    ADD CONSTRAINT print_jobs_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE SET NULL;


--
-- Name: print_jobs print_jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.print_jobs
    ADD CONSTRAINT print_jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: print_orders print_orders_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.print_orders
    ADD CONSTRAINT print_orders_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;


--
-- Name: print_orders print_orders_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.print_orders
    ADD CONSTRAINT print_orders_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: print_orders print_orders_print_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.print_orders
    ADD CONSTRAINT print_orders_print_job_id_fkey FOREIGN KEY (print_job_id) REFERENCES public.print_jobs(id) ON DELETE CASCADE;


--
-- Name: products products_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id) ON DELETE SET NULL;


--
-- Name: projects projects_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_courses user_courses_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_courses
    ADD CONSTRAINT user_courses_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id);


--
-- Name: user_courses user_courses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_courses
    ADD CONSTRAINT user_courses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_identities user_identities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_identities
    ADD CONSTRAINT user_identities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_model_configs user_model_configs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_model_configs
    ADD CONSTRAINT user_model_configs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: workflow_executions workflow_executions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_executions
    ADD CONSTRAINT workflow_executions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: workflow_executions workflow_executions_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_executions
    ADD CONSTRAINT workflow_executions_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(id) ON DELETE CASCADE;


--
-- Name: workflows workflows_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflows
    ADD CONSTRAINT workflows_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id);


--
-- Foreign Keys for community features
--

ALTER TABLE ONLY public.asset_likes
    ADD CONSTRAINT asset_likes_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.asset_likes
    ADD CONSTRAINT asset_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.asset_downloads
    ADD CONSTRAINT asset_downloads_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.asset_downloads
    ADD CONSTRAINT asset_downloads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.comments(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.comment_likes
    ADD CONSTRAINT comment_likes_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public.comments(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.comment_likes
    ADD CONSTRAINT comment_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.studio_history
    ADD CONSTRAINT studio_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.studio_history
    ADD CONSTRAINT studio_history_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.studio_jobs
    ADD CONSTRAINT studio_jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.studio_jobs
    ADD CONSTRAINT studio_jobs_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE SET NULL;

--
-- 迁移：已有库若 user_identities 缺列则补上（新建库 CREATE TABLE 已含，可忽略）
--
ALTER TABLE public.user_identities ADD COLUMN IF NOT EXISTS free_contributed integer DEFAULT 0 NOT NULL;
ALTER TABLE public.user_identities ADD COLUMN IF NOT EXISTS paid_contributed integer DEFAULT 0 NOT NULL;
ALTER TABLE public.user_identities ADD COLUMN IF NOT EXISTS redeemed_contributed integer DEFAULT 0 NOT NULL;

--
-- 迁移：积分多轨制补充兑换积分列
--
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS free_points integer DEFAULT 60;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS redeemed_points integer DEFAULT 0;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS paid_points integer DEFAULT 0;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS free_points_refreshed_at timestamp with time zone DEFAULT now();

--
-- 迁移：studio_jobs 补充异步任务扣费字段（成功后扣分）
--
ALTER TABLE public.studio_jobs ADD COLUMN IF NOT EXISTS credits_used integer DEFAULT 0;
ALTER TABLE public.studio_jobs ADD COLUMN IF NOT EXISTS charged_at timestamp with time zone;


--
-- PostgreSQL database dump complete
--

\unrestrict q7EOZ1xihsIfZaKXFA0H2N0Lq8w5S7LK5zTv1uR7foMdiHpMe6wq3SmkDWah6rH


-- ============================================
-- Migrations Schema
-- ============================================

-- Source: 001_add_mall_tables.sql (Schema)
-- ============================================
-- 商城模块数据库迁移脚本
-- 版本: v1.0
-- 日期: 2026-02-19
-- 说明: 添加商品、分类、订单明细、打印订单等表
-- ============================================

-- 1. 商品分类表
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    parent_id UUID,
    description TEXT,
    icon VARCHAR(100),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
);

-- 创建分类索引
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_active ON categories(is_active);

-- 2. 商品表
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category_id UUID,
    price NUMERIC(10,2) NOT NULL DEFAULT 0,
    price_type VARCHAR(20) DEFAULT 'fixed',
    price_unit VARCHAR(20),
    stock INTEGER DEFAULT 0,
    stock_type VARCHAR(20) DEFAULT 'limited',
    images JSONB DEFAULT '[]'::jsonb,
    specs JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) DEFAULT 'active',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

-- 创建商品索引
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_created ON products(created_at DESC);

-- 3. 订单明细表
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,
    product_id UUID,
    product_type VARCHAR(50) DEFAULT 'product',
    product_snapshot JSONB NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(10,2) NOT NULL,
    total_price NUMERIC(10,2) NOT NULL,
    specs JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

-- 创建订单明细索引
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);

-- 4. 打印订单关联表
CREATE TABLE IF NOT EXISTS print_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,
    print_job_id UUID NOT NULL,
    asset_id UUID NOT NULL,
    print_specs JSONB,
    estimated_weight NUMERIC(10,2),
    actual_weight NUMERIC(10,2),
    price_per_gram NUMERIC(10,2) DEFAULT 2.00,
    shipping_company VARCHAR(100),
    tracking_number VARCHAR(100),
    shipped_at TIMESTAMP,
    received_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (print_job_id) REFERENCES print_jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- 创建打印订单索引
CREATE INDEX IF NOT EXISTS idx_print_orders_order ON print_orders(order_id);
CREATE INDEX IF NOT EXISTS idx_print_orders_job ON print_orders(print_job_id);
CREATE INDEX IF NOT EXISTS idx_print_orders_asset ON print_orders(asset_id);

-- 5. 购物车表
CREATE TABLE IF NOT EXISTS carts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    product_id UUID NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    specs JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE(user_id, product_id)
);

-- 创建购物车索引
CREATE INDEX IF NOT EXISTS idx_carts_user ON carts(user_id);
CREATE INDEX IF NOT EXISTS idx_carts_product ON carts(product_id);


-- Source: 002_add_print_jobs_updated_at.sql
-- ============================================
-- 添加 print_jobs 表的 updated_at 字段
-- 版本: v1.1
-- 日期: 2026-02-21
-- ============================================

ALTER TABLE print_jobs 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 更新现有记录的 updated_at 为 created_at
UPDATE print_jobs SET updated_at = created_at WHERE updated_at IS NULL;


-- ============================================
-- Source: 003_add_community_posts.sql
-- 社区帖子（文字 + 图片 + 3D + 视频可选）
-- ============================================

CREATE TABLE IF NOT EXISTS community_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL,
    content TEXT DEFAULT '',
    images JSONB DEFAULT '[]'::jsonb,
    models JSONB DEFAULT '[]'::jsonb,
    videos JSONB DEFAULT '[]'::jsonb,
    like_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'published',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT community_posts_author_fkey
        FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_community_posts_author ON community_posts(author_id);
CREATE INDEX IF NOT EXISTS idx_community_posts_created ON community_posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_community_posts_status ON community_posts(status);

CREATE TABLE IF NOT EXISTS community_post_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL,
    user_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT community_post_likes_post_fkey
        FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
    CONSTRAINT community_post_likes_user_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT community_post_likes_unique UNIQUE (post_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_community_post_likes_post ON community_post_likes(post_id);
CREATE INDEX IF NOT EXISTS idx_community_post_likes_user ON community_post_likes(user_id);

CREATE TABLE IF NOT EXISTS community_post_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL,
    author_id UUID,
    parent_id UUID,
    content TEXT NOT NULL,
    images JSONB DEFAULT '[]'::jsonb,
    videos JSONB DEFAULT '[]'::jsonb,
    like_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'published',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT community_post_comments_post_fkey
        FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
    CONSTRAINT community_post_comments_author_fkey
        FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT community_post_comments_parent_fkey
        FOREIGN KEY (parent_id) REFERENCES community_post_comments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_community_post_comments_post ON community_post_comments(post_id);
CREATE INDEX IF NOT EXISTS idx_community_post_comments_parent ON community_post_comments(parent_id);
CREATE INDEX IF NOT EXISTS idx_community_post_comments_author ON community_post_comments(author_id);

CREATE TABLE IF NOT EXISTS community_post_comment_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL,
    user_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT community_post_comment_likes_comment_fkey
        FOREIGN KEY (comment_id) REFERENCES community_post_comments(id) ON DELETE CASCADE,
    CONSTRAINT community_post_comment_likes_user_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT community_post_comment_likes_unique UNIQUE (comment_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_community_post_comment_likes_comment ON community_post_comment_likes(comment_id);
CREATE INDEX IF NOT EXISTS idx_community_post_comment_likes_user ON community_post_comment_likes(user_id);

DO $$
BEGIN
    RAISE NOTICE '✅ print_jobs 表已添加 updated_at 字段';
END $$;

-- Source: 003_add_payment_id_to_orders.sql
-- 添加payment_id字段到orders表
-- 用于存储Stripe session_id或PayPal order_id

ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_id VARCHAR(255);

-- 添加索引以便快速查询
CREATE INDEX IF NOT EXISTS idx_orders_payment_id ON orders(payment_id);

-- Source: 004_add_credit_recharges_table.sql
-- 积分充值记录表
CREATE TABLE IF NOT EXISTS credit_recharges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,  -- 充值积分数量
    bonus_amount INTEGER DEFAULT 0,  -- 赠送积分数量
    total_amount INTEGER NOT NULL,  -- 总积分数量（充值+赠送）
    amount_yuan DECIMAL(10, 2) NOT NULL,  -- 充值金额（元）
    payment_method VARCHAR(50) NOT NULL,  -- 支付方式：alipay, stripe
    payment_id VARCHAR(255),  -- 第三方支付订单ID
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 状态：pending, paid, failed, cancelled
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    paid_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT credit_recharges_amount_check CHECK (amount > 0 AND amount <= 100000),
    CONSTRAINT credit_recharges_amount_yuan_check CHECK (amount_yuan > 0),
    CONSTRAINT credit_recharges_bonus_amount_check CHECK (bonus_amount >= 0),
    CONSTRAINT credit_recharges_total_amount_check CHECK (total_amount = amount + bonus_amount)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_credit_recharges_user_id ON credit_recharges(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_recharges_status ON credit_recharges(status);
CREATE INDEX IF NOT EXISTS idx_credit_recharges_created_at ON credit_recharges(created_at DESC);

-- Source: 005_add_recharge_tiers.sql (Schema)
-- 充值档位配置表
CREATE TABLE IF NOT EXISTS recharge_tiers (
    id SERIAL PRIMARY KEY,
    min_amount INTEGER NOT NULL,  -- 最低充值积分数
    bonus_rate DECIMAL(5, 2) NOT NULL DEFAULT 0,  -- 赠送比例（例如：10.00 表示赠送10%）
    bonus_fixed INTEGER DEFAULT 0,  -- 固定赠送积分数
    description VARCHAR(255),  -- 描述（如"充值1000送100"）
    is_active BOOLEAN DEFAULT TRUE,  -- 是否启用
    sort_order INTEGER DEFAULT 0,  -- 排序
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT recharge_tiers_min_amount_check CHECK (min_amount > 0),
    CONSTRAINT recharge_tiers_bonus_rate_check CHECK (bonus_rate >= 0 AND bonus_rate <= 100)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_recharge_tiers_active ON recharge_tiers(is_active, sort_order);
CREATE INDEX IF NOT EXISTS idx_recharge_tiers_min_amount ON recharge_tiers(min_amount);

-- Source: 008_add_cdk_redemption_tables.sql
-- CDK 兑换码（仅存哈希，不存明文）
CREATE TABLE IF NOT EXISTS cdk_redemption_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code_hash CHAR(64) NOT NULL UNIQUE,
    code_prefix VARCHAR(12),
    points INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    max_redeem_count INTEGER NOT NULL DEFAULT 1,
    redeemed_count INTEGER NOT NULL DEFAULT 0,
    redeemed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    redeemed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    note TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT cdk_redemption_codes_points_check CHECK (points > 0),
    CONSTRAINT cdk_redemption_codes_status_check CHECK (status IN ('active', 'used', 'disabled', 'expired')),
    CONSTRAINT cdk_redemption_codes_max_redeem_count_check CHECK (max_redeem_count > 0),
    CONSTRAINT cdk_redemption_codes_redeemed_count_check CHECK (redeemed_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_cdk_redemption_codes_status
    ON cdk_redemption_codes(status, expires_at, redeemed_count);

-- CDK 兑换流水（审计）
CREATE TABLE IF NOT EXISTS cdk_redemption_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code_id UUID NOT NULL REFERENCES cdk_redemption_codes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    points INTEGER NOT NULL,
    code_prefix VARCHAR(12),
    client_ip VARCHAR(64),
    user_agent TEXT,
    redeemed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT cdk_redemption_records_points_check CHECK (points > 0)
);

CREATE INDEX IF NOT EXISTS idx_cdk_redemption_records_user_id
    ON cdk_redemption_records(user_id, redeemed_at DESC);
CREATE INDEX IF NOT EXISTS idx_cdk_redemption_records_code_id
    ON cdk_redemption_records(code_id);


-- Source: 006_alter_print_jobs_asset_fk.sql
-- 修改 print_jobs.asset_id 外键为 ON DELETE SET NULL
-- 目的：允许删除作品时保留历史打印任务记录，将其 asset_id 置为 NULL

ALTER TABLE public.print_jobs
    DROP CONSTRAINT IF EXISTS print_jobs_asset_id_fkey;

ALTER TABLE public.print_jobs
    ADD CONSTRAINT print_jobs_asset_id_fkey
    FOREIGN KEY (asset_id)
    REFERENCES public.assets (id)
    ON DELETE SET NULL;


-- Source: 007_add_asset_downloads_table.sql
-- 社区作品下载去重表：asset_downloads
-- 作用：保证同一用户重复下载同一作品时，只计一次下载量

CREATE TABLE IF NOT EXISTS asset_downloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL,
    user_id UUID NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE asset_downloads
    ADD CONSTRAINT asset_downloads_asset_id_user_id_key UNIQUE (asset_id, user_id);

ALTER TABLE asset_downloads
    ADD CONSTRAINT asset_downloads_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE;

ALTER TABLE asset_downloads
    ADD CONSTRAINT asset_downloads_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_asset_downloads_asset ON asset_downloads(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_downloads_user ON asset_downloads(user_id);




-- ================================================================
-- 农场状态管理系统
-- 用于主平台追踪农场上线状态、打印机状态、订单分配
-- ================================================================

-- 农场状态表（主平台缓存表）
CREATE TABLE IF NOT EXISTS farm_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL UNIQUE,              -- 对应client端的merchant_id
    farm_name VARCHAR(100),                     -- 农场名称
    api_endpoint VARCHAR(255) NOT NULL,         -- 农场API地址
    api_key VARCHAR(255),                       -- API密钥（用于验证）
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'offline',       -- online/offline/busy/maintenance
    total_printers INT DEFAULT 0,               -- 总打印机数
    idle_printers INT DEFAULT 0,                -- 空闲打印机数
    busy_printers INT DEFAULT 0,                -- 忙碌打印机数
    offline_printers INT DEFAULT 0,             -- 离线打印机数
    
    -- 位置信息
    province VARCHAR(30),
    city VARCHAR(30),
    district VARCHAR(30),
    
    -- 心跳信息
    last_heartbeat TIMESTAMP,                   -- 最后心跳时间
    heartbeat_interval INT DEFAULT 30,          -- 心跳间隔（秒）
    
    -- 统计信息
    total_orders INT DEFAULT 0,                 -- 总订单数
    completed_orders INT DEFAULT 0,             -- 完成订单数
    failed_orders INT DEFAULT 0,                -- 失败订单数
    
    -- 优先级和权重
    priority INT DEFAULT 0,                     -- 优先级（数字越大越优先）
    weight INT DEFAULT 100,                     -- 权重（用于负载均衡）
    
    enabled BOOLEAN DEFAULT TRUE,               -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 打印机状态表（主平台缓存表）
CREATE TABLE IF NOT EXISTS printer_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farm_status(farm_id) ON DELETE CASCADE,
    printer_id UUID NOT NULL,                   -- 对应client端的printer_id
    printer_name VARCHAR(100),
    printer_model VARCHAR(100),
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'offline',       -- idle/printing/cooling/maintenance/error/offline
    current_order_id UUID,                      -- 当前订单ID
    
    -- 实时数据
    nozzle_temp INT,                            -- 喷头温度
    bed_temp INT,                               -- 热床温度
    print_progress INT DEFAULT 0,               -- 打印进度 0-100
    
    -- 能力信息
    max_nozzle_temp INT DEFAULT 300,
    max_bed_temp INT DEFAULT 110,
    build_volume VARCHAR(50),                   -- 打印尺寸
    supported_materials VARCHAR(200),           -- 支持材质
    
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(farm_id, printer_id)
);

-- 订单分配记录表
CREATE TABLE IF NOT EXISTS order_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,                     -- 主平台订单ID
    farm_id UUID NOT NULL REFERENCES farm_status(farm_id),
    printer_id UUID REFERENCES printer_status(printer_id),
    
    status VARCHAR(20) DEFAULT 'assigned',      -- assigned/accepted/rejected/printing/completed/failed
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- 失败信息
    failure_reason TEXT,
    retry_count INT DEFAULT 0,
    
    UNIQUE(order_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_farm_status_status ON farm_status(status);
CREATE INDEX IF NOT EXISTS idx_farm_status_enabled ON farm_status(enabled);
CREATE INDEX IF NOT EXISTS idx_farm_last_heartbeat ON farm_status(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_printer_status_farm ON printer_status(farm_id);
CREATE INDEX IF NOT EXISTS idx_printer_status_status ON printer_status(status);
CREATE INDEX IF NOT EXISTS idx_order_assignments_order ON order_assignments(order_id);
CREATE INDEX IF NOT EXISTS idx_order_assignments_farm ON order_assignments(farm_id);
CREATE INDEX IF NOT EXISTS idx_order_assignments_status ON order_assignments(status);

-- 注释
COMMENT ON TABLE farm_status IS '农场状态缓存表，记录所有农场的实时状态';
COMMENT ON TABLE printer_status IS '打印机状态缓存表，记录所有打印机的实时状态';
COMMENT ON TABLE order_assignments IS '订单分配记录表，记录订单派发给哪个农场';

COMMENT ON COLUMN farm_status.status IS 'online-在线, offline-离线, busy-繁忙, maintenance-维护中';
COMMENT ON COLUMN farm_status.last_heartbeat IS '最后心跳时间，超过3倍heartbeat_interval视为离线';
COMMENT ON COLUMN printer_status.status IS 'idle-空闲, printing-打印中, cooling-冷却中, maintenance-维护, error-错误, offline-离线';


-- ============================================================================
-- 积分系统重构 - 充值订单追踪和退款功能
-- ============================================================================

-- 为 credit_recharges 表添加新字段
ALTER TABLE credit_recharges 
ADD COLUMN IF NOT EXISTS remaining_credits INTEGER DEFAULT 0;

ALTER TABLE credit_recharges 
ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE credit_recharges 
ADD COLUMN IF NOT EXISTS refund_amount DECIMAL(10, 2);

ALTER TABLE credit_recharges 
ADD COLUMN IF NOT EXISTS refund_reason TEXT;

-- 添加约束
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'credit_recharges_remaining_check'
    ) THEN
        ALTER TABLE credit_recharges 
        ADD CONSTRAINT credit_recharges_remaining_check 
        CHECK (remaining_credits >= 0 AND remaining_credits <= total_amount);
    END IF;
END $$;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_credit_recharges_paid_at ON credit_recharges(paid_at);
CREATE INDEX IF NOT EXISTS idx_credit_recharges_refundable ON credit_recharges(user_id, status, paid_at) 
WHERE status = 'paid' AND refunded_at IS NULL;

-- 创建积分消耗记录表
CREATE TABLE IF NOT EXISTS credit_consumption_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recharge_id UUID REFERENCES credit_recharges(id) ON DELETE SET NULL,
    amount INTEGER NOT NULL,
    credit_type VARCHAR(20) NOT NULL,
    reason VARCHAR(100),
    related_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT credit_consumption_amount_check CHECK (amount > 0)
);

-- 创建消耗记录索引
CREATE INDEX IF NOT EXISTS idx_credit_consumption_user ON credit_consumption_records(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_consumption_recharge ON credit_consumption_records(recharge_id);
CREATE INDEX IF NOT EXISTS idx_credit_consumption_type ON credit_consumption_records(credit_type);

-- 注释
COMMENT ON TABLE credit_consumption_records IS '积分消耗记录表，追踪每笔积分的使用情况';
COMMENT ON COLUMN credit_recharges.remaining_credits IS '充值订单剩余积分，用于FIFO消耗和退款计算';
COMMENT ON COLUMN credit_recharges.refunded_at IS '退款时间';
COMMENT ON COLUMN credit_recharges.refund_amount IS '退款金额（元）';
COMMENT ON COLUMN credit_consumption_records.credit_type IS '积分类型：free-免费, redeemed-兑换, paid-付费';
COMMENT ON COLUMN credit_consumption_records.reason IS '消耗原因：generate_3d, purchase_product等';
