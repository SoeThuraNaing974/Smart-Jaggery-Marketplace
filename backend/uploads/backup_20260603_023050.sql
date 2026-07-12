--
-- PostgreSQL database dump
--

\restrict PVohtzFfsBLVDJwyZNOmjjxqV6kbywwKdIKO75f0rqXEifPcqTZETuEptIKhgjd

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

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
-- Name: abandoned_carts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.abandoned_carts (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    items_json jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.abandoned_carts OWNER TO postgres;

--
-- Name: abandoned_carts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.abandoned_carts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.abandoned_carts_id_seq OWNER TO postgres;

--
-- Name: abandoned_carts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.abandoned_carts_id_seq OWNED BY public.abandoned_carts.id;


--
-- Name: announcements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.announcements (
    id integer NOT NULL,
    title character varying(160) NOT NULL,
    message text NOT NULL,
    created_by_admin_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone
);


ALTER TABLE public.announcements OWNER TO postgres;

--
-- Name: announcements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.announcements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.announcements_id_seq OWNER TO postgres;

--
-- Name: announcements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.announcements_id_seq OWNED BY public.announcements.id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    user_id integer,
    action character varying(80) NOT NULL,
    details text,
    ip_address character varying(45),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.audit_logs OWNER TO postgres;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO postgres;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: delivery_charges; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.delivery_charges (
    id integer NOT NULL,
    pincode character varying(12) NOT NULL,
    charge_amount numeric(10,2) DEFAULT 0 NOT NULL
);


ALTER TABLE public.delivery_charges OWNER TO postgres;

--
-- Name: delivery_charges_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.delivery_charges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.delivery_charges_id_seq OWNER TO postgres;

--
-- Name: delivery_charges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.delivery_charges_id_seq OWNED BY public.delivery_charges.id;


--
-- Name: jaggery_batches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jaggery_batches (
    id integer NOT NULL,
    warehouse_id integer NOT NULL,
    batch_id character varying(60) NOT NULL,
    grade character varying(1) NOT NULL,
    qty_kg numeric(10,2) NOT NULL,
    harvest_date date NOT NULL,
    price_per_kg numeric(10,2) NOT NULL,
    certificate_path character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    image_path character varying(255),
    description text,
    CONSTRAINT jaggery_batches_grade_check CHECK (((grade)::text = ANY ((ARRAY['A'::character varying, 'B'::character varying, 'C'::character varying, 'D'::character varying])::text[]))),
    CONSTRAINT jaggery_batches_price_per_kg_check CHECK ((price_per_kg >= (0)::numeric)),
    CONSTRAINT jaggery_batches_qty_kg_check CHECK ((qty_kg >= (0)::numeric))
);


ALTER TABLE public.jaggery_batches OWNER TO postgres;

--
-- Name: jaggery_batches_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.jaggery_batches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.jaggery_batches_id_seq OWNER TO postgres;

--
-- Name: jaggery_batches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.jaggery_batches_id_seq OWNED BY public.jaggery_batches.id;


--
-- Name: order_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.order_items (
    id integer NOT NULL,
    order_id integer NOT NULL,
    batch_pk integer NOT NULL,
    qty_kg numeric(10,2) NOT NULL,
    unit_price numeric(10,2) NOT NULL,
    line_total numeric(12,2) NOT NULL,
    CONSTRAINT order_items_qty_kg_check CHECK ((qty_kg > (0)::numeric))
);


ALTER TABLE public.order_items OWNER TO postgres;

--
-- Name: order_items_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.order_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_items_id_seq OWNER TO postgres;

--
-- Name: order_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.order_items_id_seq OWNED BY public.order_items.id;


--
-- Name: order_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.order_messages (
    id integer NOT NULL,
    order_id integer NOT NULL,
    sender_id integer,
    sender_role character varying(20) NOT NULL,
    message text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.order_messages OWNER TO postgres;

--
-- Name: order_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.order_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_messages_id_seq OWNER TO postgres;

--
-- Name: order_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.order_messages_id_seq OWNED BY public.order_messages.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.orders (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    assigned_warehouse_id integer,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    delivery_address text NOT NULL,
    preferred_date date,
    subtotal numeric(12,2) DEFAULT 0 NOT NULL,
    discount_amount numeric(12,2) DEFAULT 0 NOT NULL,
    total_price numeric(12,2) DEFAULT 0 NOT NULL,
    promotion_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    pincode character varying(12),
    delivery_charge numeric(10,2) DEFAULT 0 NOT NULL,
    delivered_at timestamp with time zone,
    CONSTRAINT orders_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'assigned'::character varying, 'packed'::character varying, 'shipped'::character varying, 'delivered'::character varying, 'cancelled'::character varying])::text[])))
);


ALTER TABLE public.orders OWNER TO postgres;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orders_id_seq OWNER TO postgres;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    warehouse_id integer NOT NULL,
    subscription_id integer,
    plan_id integer,
    amount numeric(10,2) NOT NULL,
    method character varying(20) NOT NULL,
    payer character varying(120),
    reference character varying(120),
    status character varying(20) DEFAULT 'paid'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT payments_method_check CHECK (((method)::text = ANY ((ARRAY['kpay'::character varying, 'wavepay'::character varying, 'ayapay'::character varying, 'cbpay'::character varying, 'yomapay'::character varying, 'bank'::character varying])::text[])))
);


ALTER TABLE public.payments OWNER TO postgres;

--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payments_id_seq OWNER TO postgres;

--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: price_alerts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.price_alerts (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    batch_id integer NOT NULL,
    desired_price numeric(10,2) NOT NULL,
    is_notified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.price_alerts OWNER TO postgres;

--
-- Name: price_alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.price_alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.price_alerts_id_seq OWNER TO postgres;

--
-- Name: price_alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.price_alerts_id_seq OWNED BY public.price_alerts.id;


--
-- Name: product_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.product_requests (
    id integer NOT NULL,
    warehouse_id integer NOT NULL,
    requested_by integer,
    batch_code character varying(60) NOT NULL,
    grade character varying(1) NOT NULL,
    qty_kg numeric(10,2) NOT NULL,
    harvest_date date NOT NULL,
    price_per_kg numeric(10,2) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    admin_note text,
    reviewed_by integer,
    created_batch_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    reviewed_at timestamp with time zone,
    image_path character varying(255),
    description text,
    CONSTRAINT product_requests_grade_check CHECK (((grade)::text = ANY ((ARRAY['A'::character varying, 'B'::character varying, 'C'::character varying, 'D'::character varying])::text[]))),
    CONSTRAINT product_requests_price_per_kg_check CHECK ((price_per_kg >= (0)::numeric)),
    CONSTRAINT product_requests_qty_kg_check CHECK ((qty_kg >= (0)::numeric)),
    CONSTRAINT product_requests_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying])::text[])))
);


ALTER TABLE public.product_requests OWNER TO postgres;

--
-- Name: product_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.product_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.product_requests_id_seq OWNER TO postgres;

--
-- Name: product_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.product_requests_id_seq OWNED BY public.product_requests.id;


--
-- Name: promotions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.promotions (
    id integer NOT NULL,
    title character varying(160) NOT NULL,
    discount_percent numeric(5,2) NOT NULL,
    min_qty numeric(10,2) DEFAULT 0 NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_promo_dates CHECK ((end_date >= start_date)),
    CONSTRAINT promotions_discount_percent_check CHECK (((discount_percent >= (0)::numeric) AND (discount_percent <= (100)::numeric)))
);


ALTER TABLE public.promotions OWNER TO postgres;

--
-- Name: promotions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.promotions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.promotions_id_seq OWNER TO postgres;

--
-- Name: promotions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.promotions_id_seq OWNED BY public.promotions.id;


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    order_id integer NOT NULL,
    customer_id integer NOT NULL,
    warehouse_id integer NOT NULL,
    rating smallint NOT NULL,
    comment text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT reviews_rating_check CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.reviews OWNER TO postgres;

--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reviews_id_seq OWNER TO postgres;

--
-- Name: reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
-- Name: stock_transfers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stock_transfers (
    id integer NOT NULL,
    from_warehouse_id integer NOT NULL,
    to_warehouse_id integer NOT NULL,
    batch_id integer NOT NULL,
    quantity_kg numeric(10,2) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    approved_by_admin_id integer,
    CONSTRAINT stock_transfers_quantity_kg_check CHECK ((quantity_kg > (0)::numeric)),
    CONSTRAINT stock_transfers_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying, 'completed'::character varying])::text[])))
);


ALTER TABLE public.stock_transfers OWNER TO postgres;

--
-- Name: stock_transfers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stock_transfers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stock_transfers_id_seq OWNER TO postgres;

--
-- Name: stock_transfers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stock_transfers_id_seq OWNED BY public.stock_transfers.id;


--
-- Name: subscription_plans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subscription_plans (
    id integer NOT NULL,
    name character varying(80) NOT NULL,
    duration_months integer NOT NULL,
    price numeric(10,2) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT subscription_plans_duration_months_check CHECK ((duration_months > 0)),
    CONSTRAINT subscription_plans_price_check CHECK ((price >= (0)::numeric))
);


ALTER TABLE public.subscription_plans OWNER TO postgres;

--
-- Name: subscription_plans_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.subscription_plans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.subscription_plans_id_seq OWNER TO postgres;

--
-- Name: subscription_plans_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.subscription_plans_id_seq OWNED BY public.subscription_plans.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    name character varying(120) NOT NULL,
    email character varying(160) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(20) DEFAULT 'customer'::character varying NOT NULL,
    warehouse_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    phone character varying(30),
    address text,
    pincode character varying(12),
    payment_pin_hash character varying(255),
    pin_reset_code character varying(255),
    pin_reset_expires timestamp with time zone,
    CONSTRAINT chk_staff_warehouse CHECK ((((role)::text = 'warehouse_staff'::text) OR (warehouse_id IS NULL))),
    CONSTRAINT users_role_check CHECK (((role)::text = ANY ((ARRAY['customer'::character varying, 'warehouse_staff'::character varying, 'admin'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: warehouse_subscriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.warehouse_subscriptions (
    id integer NOT NULL,
    warehouse_id integer NOT NULL,
    plan_id integer,
    start_date date NOT NULL,
    end_date date NOT NULL,
    price_paid numeric(10,2) DEFAULT 0 NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT warehouse_subscriptions_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'cancelled'::character varying])::text[])))
);


ALTER TABLE public.warehouse_subscriptions OWNER TO postgres;

--
-- Name: warehouse_subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.warehouse_subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.warehouse_subscriptions_id_seq OWNER TO postgres;

--
-- Name: warehouse_subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.warehouse_subscriptions_id_seq OWNED BY public.warehouse_subscriptions.id;


--
-- Name: warehouses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.warehouses (
    id integer NOT NULL,
    name character varying(120) NOT NULL,
    location character varying(200) NOT NULL,
    phone character varying(30),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    pincode character varying(12),
    manager_name character varying(120)
);


ALTER TABLE public.warehouses OWNER TO postgres;

--
-- Name: warehouses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.warehouses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.warehouses_id_seq OWNER TO postgres;

--
-- Name: warehouses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.warehouses_id_seq OWNED BY public.warehouses.id;


--
-- Name: wishlist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.wishlist (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    batch_id integer NOT NULL,
    added_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.wishlist OWNER TO postgres;

--
-- Name: wishlist_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.wishlist_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wishlist_id_seq OWNER TO postgres;

--
-- Name: wishlist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.wishlist_id_seq OWNED BY public.wishlist.id;


--
-- Name: abandoned_carts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.abandoned_carts ALTER COLUMN id SET DEFAULT nextval('public.abandoned_carts_id_seq'::regclass);


--
-- Name: announcements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.announcements ALTER COLUMN id SET DEFAULT nextval('public.announcements_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: delivery_charges id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.delivery_charges ALTER COLUMN id SET DEFAULT nextval('public.delivery_charges_id_seq'::regclass);


--
-- Name: jaggery_batches id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jaggery_batches ALTER COLUMN id SET DEFAULT nextval('public.jaggery_batches_id_seq'::regclass);


--
-- Name: order_items id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items ALTER COLUMN id SET DEFAULT nextval('public.order_items_id_seq'::regclass);


--
-- Name: order_messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_messages ALTER COLUMN id SET DEFAULT nextval('public.order_messages_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: price_alerts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.price_alerts ALTER COLUMN id SET DEFAULT nextval('public.price_alerts_id_seq'::regclass);


--
-- Name: product_requests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_requests ALTER COLUMN id SET DEFAULT nextval('public.product_requests_id_seq'::regclass);


--
-- Name: promotions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.promotions ALTER COLUMN id SET DEFAULT nextval('public.promotions_id_seq'::regclass);


--
-- Name: reviews id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
-- Name: stock_transfers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_transfers ALTER COLUMN id SET DEFAULT nextval('public.stock_transfers_id_seq'::regclass);


--
-- Name: subscription_plans id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscription_plans ALTER COLUMN id SET DEFAULT nextval('public.subscription_plans_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: warehouse_subscriptions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.warehouse_subscriptions ALTER COLUMN id SET DEFAULT nextval('public.warehouse_subscriptions_id_seq'::regclass);


--
-- Name: warehouses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.warehouses ALTER COLUMN id SET DEFAULT nextval('public.warehouses_id_seq'::regclass);


--
-- Name: wishlist id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.wishlist ALTER COLUMN id SET DEFAULT nextval('public.wishlist_id_seq'::regclass);


--
-- Data for Name: abandoned_carts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.abandoned_carts (id, customer_id, items_json, created_at) FROM stdin;
\.


--
-- Data for Name: announcements; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.announcements (id, title, message, created_by_admin_id, created_at, expires_at) FROM stdin;
1	Welcome	Fresh jaggery in stock	1	2026-06-02 08:55:05.849203+06:30	\N
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.audit_logs (id, user_id, action, details, ip_address, created_at) FROM stdin;
1	3	login	customer login	127.0.0.1	2026-06-02 08:55:04.05405+06:30
2	2	login	warehouse_staff login	127.0.0.1	2026-06-02 08:55:04.676712+06:30
3	1	login	admin login	127.0.0.1	2026-06-02 08:55:05.058654+06:30
4	3	login	customer login	127.0.0.1	2026-06-02 08:56:49.826217+06:30
5	2	login	warehouse_staff login	127.0.0.1	2026-06-02 08:56:50.271935+06:30
6	1	login	admin login	127.0.0.1	2026-06-02 08:56:50.66492+06:30
7	3	login	customer login	127.0.0.1	2026-06-02 09:06:01.259558+06:30
8	2	login	warehouse_staff login	127.0.0.1	2026-06-02 09:06:01.676597+06:30
9	1	login	admin login	127.0.0.1	2026-06-02 09:06:02.154165+06:30
10	3	login	customer login	127.0.0.1	2026-06-02 09:16:05.708311+06:30
11	2	login	warehouse_staff login	127.0.0.1	2026-06-02 09:16:06.105115+06:30
12	1	login	admin login	127.0.0.1	2026-06-02 09:16:06.409343+06:30
13	3	login	customer login	127.0.0.1	2026-06-02 09:16:07.037625+06:30
14	1	bulk_email	dry_run to 1 recipients: Fresh stock!	127.0.0.1	2026-06-02 09:16:07.094044+06:30
15	3	login	customer login	127.0.0.1	2026-06-02 09:19:15.379686+06:30
16	3	login	customer login	127.0.0.1	2026-06-02 09:21:15.069019+06:30
17	2	login	warehouse_staff login	127.0.0.1	2026-06-02 09:21:15.359144+06:30
18	1	login	admin login	127.0.0.1	2026-06-02 09:21:15.629728+06:30
19	3	login	customer login	127.0.0.1	2026-06-02 09:22:57.556706+06:30
20	3	login	customer login	127.0.0.1	2026-06-02 09:23:31.915391+06:30
21	2	login	warehouse_staff login	127.0.0.1	2026-06-02 09:23:32.198896+06:30
22	1	login	admin login	127.0.0.1	2026-06-02 09:23:32.465686+06:30
23	1	order_assigned	order #4 -> Kolhapur Central	127.0.0.1	2026-06-02 09:23:32.527942+06:30
24	1	bulk_email	dry_run to 1 recipients: Fresh stock!	127.0.0.1	2026-06-02 09:23:32.636691+06:30
25	1	login	admin login	127.0.0.1	2026-06-02 09:31:11.802644+06:30
26	3	login	customer login	127.0.0.1	2026-06-02 09:32:27.419888+06:30
27	3	profile_update	\N	127.0.0.1	2026-06-02 09:42:05.488494+06:30
28	1	login	admin login	127.0.0.1	2026-06-02 09:51:54.855864+06:30
29	1	batch_create	ADM-TEST-1 @ WH#1	127.0.0.1	2026-06-02 09:53:31.802099+06:30
30	1	promotion_update	10% off on 5kg+	127.0.0.1	2026-06-02 09:59:00.611539+06:30
31	2	login	warehouse_staff login	127.0.0.1	2026-06-02 10:11:36.298368+06:30
32	2	subscription_purchase	1 Year for WH#1	127.0.0.1	2026-06-02 10:12:11.623243+06:30
33	1	login	admin login	127.0.0.1	2026-06-02 12:14:15.190701+06:30
34	1	batch_image	JAG-2026-001 -> batch_JAG-2026-001_0504a9f2.png	127.0.0.1	2026-06-02 12:14:15.437761+06:30
35	3	login	customer login	127.0.0.1	2026-06-02 12:15:07.391998+06:30
36	2	login	warehouse_staff login	127.0.0.1	2026-06-02 12:25:32.646839+06:30
37	2	product_request	WH-REQ-2026 from WH#1	127.0.0.1	2026-06-02 12:25:40.018453+06:30
38	1	login	admin login	127.0.0.1	2026-06-02 12:26:19.07825+06:30
39	1	product_request_approved	WH-REQ-2026 -> batch #5	127.0.0.1	2026-06-02 12:26:45.396604+06:30
40	1	login	admin login	127.0.0.1	2026-06-02 12:33:42.060632+06:30
41	1	plan_update	1 Month	127.0.0.1	2026-06-02 12:35:46.119933+06:30
42	1	plan_update	1 Month	127.0.0.1	2026-06-02 12:35:59.985862+06:30
43	2	login	warehouse_staff login	127.0.0.1	2026-06-02 12:37:20.551837+06:30
44	2	subscription_purchase	2 Months for WH#1	127.0.0.1	2026-06-02 12:39:36.301794+06:30
45	2	subscription_purchase	1 Month for WH#1	127.0.0.1	2026-06-02 12:39:56.31471+06:30
46	2	login	warehouse_staff login	127.0.0.1	2026-06-02 12:52:16.328807+06:30
47	2	subscription_payment	6 Months via wavepay ref WAVE-TXN-55012 (WH#1)	127.0.0.1	2026-06-02 12:53:35.899672+06:30
48	2	subscription_payment	1 Month via kpay ref rrttyy2234 (WH#1)	127.0.0.1	2026-06-02 12:56:01.130702+06:30
49	2	login	warehouse_staff login	127.0.0.1	2026-06-02 12:58:45.030927+06:30
50	2	login	warehouse_staff login	127.0.0.1	2026-06-02 13:02:30.226934+06:30
51	2	login	warehouse_staff login	127.0.0.1	2026-06-02 13:04:20.244592+06:30
52	2	subscription_payment	1 Month via yomapay ref YOMA-TXN-2026 (WH#1)	127.0.0.1	2026-06-02 13:04:20.595312+06:30
53	2	subscription_payment	1 Month via ayapay ref money (WH#1)	127.0.0.1	2026-06-02 13:07:34.263226+06:30
54	2	login	warehouse_staff login	127.0.0.1	2026-06-02 15:28:57.952786+06:30
55	2	login	warehouse_staff login	127.0.0.1	2026-06-02 15:35:06.002931+06:30
56	2	subscription_payment	1 Month via yomapay ref YOMA-PWD-OK (WH#1)	127.0.0.1	2026-06-02 15:35:33.515554+06:30
57	2	login	warehouse_staff login	127.0.0.1	2026-06-02 15:36:07.870873+06:30
58	2	login	warehouse_staff login	127.0.0.1	2026-06-02 15:48:16.742903+06:30
59	2	payment_pin_set	\N	127.0.0.1	2026-06-02 15:48:30.592523+06:30
60	2	subscription_payment	1 Month via yomapay ref PIN-TEST-OK (WH#1)	127.0.0.1	2026-06-02 15:49:36.858957+06:30
61	2	login	warehouse_staff login	127.0.0.1	2026-06-02 15:50:16.076381+06:30
62	2	payment_pin_set	\N	127.0.0.1	2026-06-02 15:53:51.351116+06:30
63	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:01:18.748431+06:30
64	2	subscription_payment	1 Month via kpay ref money (WH#1)	127.0.0.1	2026-06-02 16:02:11.008542+06:30
65	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:08:25.756808+06:30
66	2	payment_pin_set	\N	127.0.0.1	2026-06-02 16:10:11.469428+06:30
67	2	subscription_payment	1 Month via kpay ref KPAY-CREATE-1 (WH#1)	127.0.0.1	2026-06-02 16:10:11.536116+06:30
68	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:10:39.056316+06:30
69	2	subscription_payment	1 Month via kpay ref KPAY-ENTER-1 (WH#1)	127.0.0.1	2026-06-02 16:11:11.781146+06:30
70	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:11:27.81988+06:30
71	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:18:52.51366+06:30
72	2	payment_pin_set	\N	127.0.0.1	2026-06-02 16:20:04.719435+06:30
73	2	subscription_payment	1 Month via kpay ref KPAY-RESET-1 (WH#1)	127.0.0.1	2026-06-02 16:20:04.764091+06:30
74	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:20:26.972338+06:30
75	2	password_change	\N	127.0.0.1	2026-06-02 16:24:26.519954+06:30
76	2	password_change	\N	127.0.0.1	2026-06-02 16:25:24.164189+06:30
77	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:30:43.332966+06:30
78	2	pin_reset_requested	s***@jaggery.local	127.0.0.1	2026-06-02 16:31:10.485763+06:30
79	2	pin_reset_requested	s***@jaggery.local	127.0.0.1	2026-06-02 16:32:27.017123+06:30
80	2	pin_reset_requested	s***@jaggery.local	127.0.0.1	2026-06-02 16:35:02.250835+06:30
81	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:35:21.269287+06:30
82	2	pin_reset_requested	s***@jaggery.local	127.0.0.1	2026-06-02 16:35:21.868791+06:30
83	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:37:31.252959+06:30
84	2	pin_reset_requested	s***@jaggery.local	127.0.0.1	2026-06-02 16:37:32.299326+06:30
85	2	pin_reset_requested	s***@jaggery.local	127.0.0.1	2026-06-02 16:41:06.365625+06:30
86	2	payment_pin_reset	\N	127.0.0.1	2026-06-02 16:41:09.201473+06:30
87	2	subscription_payment	1 Month via kpay ref KPAY-OTP-FINAL (WH#1)	127.0.0.1	2026-06-02 16:41:09.267878+06:30
88	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:41:31.153829+06:30
89	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:43:21.106372+06:30
90	2	login	warehouse_staff login	127.0.0.1	2026-06-02 16:43:55.418969+06:30
91	2	payment_pin_set	\N	127.0.0.1	2026-06-02 16:43:55.949448+06:30
92	2	subscription_payment	1 Month via kpay ref money (WH#1)	127.0.0.1	2026-06-02 16:47:27.235771+06:30
93	2	profile_update	\N	127.0.0.1	2026-06-02 16:59:52.592853+06:30
94	2	profile_update	\N	127.0.0.1	2026-06-02 17:09:59.442107+06:30
95	2	profile_update	\N	127.0.0.1	2026-06-02 17:10:09.359674+06:30
96	2	profile_update	\N	127.0.0.1	2026-06-02 17:10:12.819325+06:30
97	2	login	warehouse_staff login	127.0.0.1	2026-06-02 17:28:21.795454+06:30
98	2	subscription_payment	1 Month via kpay ref money (WH#1)	127.0.0.1	2026-06-02 17:29:05.043187+06:30
99	2	login	warehouse_staff login	127.0.0.1	2026-06-02 17:42:59.496546+06:30
100	2	login	warehouse_staff login	127.0.0.1	2026-06-02 17:43:39.451215+06:30
101	1	login	admin login	127.0.0.1	2026-06-02 17:50:53.887224+06:30
102	1	batch_create	GRADE-D-TEST @ WH#1	127.0.0.1	2026-06-02 17:50:54.03798+06:30
103	1	login	admin login	127.0.0.1	2026-06-02 17:50:54.726642+06:30
104	3	login	customer login	127.0.0.1	2026-06-02 17:52:10.297021+06:30
105	3	login	customer login	127.0.0.1	2026-06-02 18:03:01.405106+06:30
106	3	login	customer login	127.0.0.1	2026-06-02 18:03:02.259532+06:30
107	2	login	warehouse_staff login	127.0.0.1	2026-06-02 18:04:11.566462+06:30
108	1	login	admin login	127.0.0.1	2026-06-02 18:13:37.784569+06:30
109	3	login	customer login	127.0.0.1	2026-06-02 18:13:38.703504+06:30
110	1	login	admin login	127.0.0.1	2026-06-02 18:14:09.937645+06:30
111	2	login	warehouse_staff login	127.0.0.1	2026-06-02 18:14:37.026522+06:30
112	2	product_request	DESC-DEMO from WH#1	127.0.0.1	2026-06-02 18:14:37.324925+06:30
113	1	login	admin login	127.0.0.1	2026-06-02 18:14:37.832158+06:30
114	1	product_request_approved	DESC-DEMO -> batch #7	127.0.0.1	2026-06-02 18:14:37.875262+06:30
115	3	login	customer login	127.0.0.1	2026-06-02 18:14:38.375646+06:30
116	3	login	customer login	127.0.0.1	2026-06-02 18:15:11.964636+06:30
117	3	login	customer login	127.0.0.1	2026-06-02 18:21:58.465939+06:30
118	3	login	customer login	127.0.0.1	2026-06-02 18:23:08.590297+06:30
119	2	login	warehouse_staff login	127.0.0.1	2026-06-02 18:25:13.040304+06:30
120	3	login	customer login	127.0.0.1	2026-06-02 18:25:34.509042+06:30
121	3	login	customer login	127.0.0.1	2026-06-02 18:26:51.28855+06:30
122	3	login	customer login	127.0.0.1	2026-06-02 18:37:24.407775+06:30
123	3	login	customer login	127.0.0.1	2026-06-02 18:45:51.08622+06:30
124	3	login	customer login	127.0.0.1	2026-06-02 18:49:23.41082+06:30
125	3	login	customer login	127.0.0.1	2026-06-02 18:52:09.59446+06:30
126	3	login	customer login	127.0.0.1	2026-06-02 19:00:14.603176+06:30
127	2	login	warehouse_staff login	127.0.0.1	2026-06-02 19:04:22.704175+06:30
128	2	login	warehouse_staff login	127.0.0.1	2026-06-02 19:06:58.923892+06:30
129	3	login	customer login	127.0.0.1	2026-06-02 19:08:19.203929+06:30
130	1	login	admin login	127.0.0.1	2026-06-02 19:13:12.141626+06:30
131	1	login	admin login	127.0.0.1	2026-06-02 19:16:38.190031+06:30
132	3	login	customer login	127.0.0.1	2026-06-02 19:22:11.258914+06:30
133	3	login	customer login	127.0.0.1	2026-06-02 19:22:37.914297+06:30
134	3	login	customer login	127.0.0.1	2026-06-02 19:23:44.379665+06:30
135	3	login	customer login	127.0.0.1	2026-06-02 19:24:30.567746+06:30
136	3	login	customer login	127.0.0.1	2026-06-02 19:27:39.858683+06:30
137	3	login	customer login	127.0.0.1	2026-06-02 19:31:22.261758+06:30
138	2	login	warehouse_staff login	127.0.0.1	2026-06-02 19:36:43.998948+06:30
139	3	login	customer login	127.0.0.1	2026-06-02 19:49:43.501823+06:30
140	1	login	admin login	127.0.0.1	2026-06-02 19:57:51.358744+06:30
141	3	profile_update	\N	127.0.0.1	2026-06-02 20:04:47.222512+06:30
142	3	login	customer login	127.0.0.1	2026-06-02 20:12:32.392152+06:30
143	1	login	admin login	127.0.0.1	2026-06-02 20:12:33.224058+06:30
144	1	login	admin login	127.0.0.1	2026-06-02 20:16:11.621962+06:30
145	1	login	admin login	127.0.0.1	2026-06-02 20:20:53.521892+06:30
146	1	login	admin login	127.0.0.1	2026-06-02 20:47:27.523965+06:30
147	3	login	customer login	127.0.0.1	2026-06-03 02:16:41.532228+06:30
148	3	login	customer login	127.0.0.1	2026-06-03 02:17:50.9293+06:30
149	3	login	customer login	127.0.0.1	2026-06-03 02:19:48.758159+06:30
150	3	login	customer login	127.0.0.1	2026-06-03 02:24:44.712582+06:30
151	1	login	admin login	127.0.0.1	2026-06-03 02:26:42.84703+06:30
\.


--
-- Data for Name: delivery_charges; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.delivery_charges (id, pincode, charge_amount) FROM stdin;
1	416001	50.00
\.


--
-- Data for Name: jaggery_batches; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.jaggery_batches (id, warehouse_id, batch_id, grade, qty_kg, harvest_date, price_per_kg, certificate_path, created_at, is_active, image_path, description) FROM stdin;
2	1	Pure Cane Jaggery Block	B	38.50	2026-04-03	45.00	\N	2026-06-02 08:24:24.744407+06:30	t	\N	\N
3	1	Traditional Jaggery	C	200.00	2025-07-17	30.00	\N	2026-06-02 08:24:24.744409+06:30	t	\N	\N
4	1	Organic Jaggery Powder	A	75.00	2026-05-15	52.00	\N	2026-06-02 09:53:31.806736+06:30	t	\N	\N
5	1	Palm Jaggery	A	90.00	2026-05-20	58.00	\N	2026-06-02 12:26:45.380589+06:30	t	\N	\N
6	1	Economy Jaggery	D	40.00	2026-05-15	35.00	\N	2026-06-02 17:50:54.039923+06:30	t	\N	\N
7	1	Coconut Jaggery	B	20.00	2026-05-25	45.00	\N	2026-06-02 18:14:37.87327+06:30	t	\N	Pure sugarcane jaggery
1	1	Premium Sugarcane Jaggery	A	114.00	2026-05-03	60.00	\N	2026-06-02 08:24:24.744404+06:30	t	batch_JAG-2026-001_0504a9f2.png	Made from 100% organic sugarcane juice, slow-boiled in traditional iron woks with no chemicals or refined sugar. Rich in iron, magnesium and potassium. Boosts immunity, aids digestion, cleanses the liver, and gives natural sustained energy. Great as a healthy sweetener for tea, sweets and daily cooking.
\.


--
-- Data for Name: order_items; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.order_items (id, order_id, batch_pk, qty_kg, unit_price, line_total) FROM stdin;
1	1	1	4.00	60.00	240.00
2	2	2	1.50	45.00	67.50
3	3	1	2.00	60.00	120.00
4	4	1	2.00	60.00	120.00
5	5	1	2.00	60.00	120.00
\.


--
-- Data for Name: order_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.order_messages (id, order_id, sender_id, sender_role, message, created_at) FROM stdin;
1	4	3	customer	When will it ship?	2026-06-02 09:23:32.555783+06:30
2	4	2	warehouse_staff	Packing today, ships tomorrow.	2026-06-02 09:23:32.589993+06:30
3	4	2	warehouse_staff	hello	2026-06-02 19:40:31.208465+06:30
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.orders (id, customer_id, assigned_warehouse_id, status, delivery_address, preferred_date, subtotal, discount_amount, total_price, promotion_id, created_at, updated_at, pincode, delivery_charge, delivered_at) FROM stdin;
1	3	\N	pending	Yangon	2026-06-03	240.00	0.00	240.00	\N	2026-06-02 08:37:31.563651+06:30	2026-06-02 08:37:31.563664+06:30	\N	0.00	\N
2	3	\N	pending	Mandalay	2026-06-03	67.50	0.00	67.50	\N	2026-06-02 08:38:20.131543+06:30	2026-06-02 08:38:20.131555+06:30	\N	0.00	\N
4	3	1	shipped	MG Road	\N	120.00	0.00	120.00	\N	2026-06-02 09:23:32.495015+06:30	2026-06-02 19:40:15.524303+06:30	\N	0.00	\N
5	3	\N	cancelled	MG Road	\N	120.00	0.00	120.00	\N	2026-06-02 19:50:24.271931+06:30	2026-06-02 19:50:39.763867+06:30	\N	0.00	\N
3	3	\N	cancelled	MG Road	\N	120.00	0.00	120.00	\N	2026-06-02 09:19:15.500744+06:30	2026-06-02 19:51:18.82598+06:30	\N	0.00	\N
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payments (id, warehouse_id, subscription_id, plan_id, amount, method, payer, reference, status, created_at) FROM stdin;
13	1	16	1	599.00	kpay	09699252008	money	paid	2026-06-02 17:29:05.045662+06:30
\.


--
-- Data for Name: price_alerts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.price_alerts (id, customer_id, batch_id, desired_price, is_notified, created_at) FROM stdin;
1	3	1	55.00	f	2026-06-02 08:55:05.272316+06:30
2	3	5	0.00	f	2026-06-02 18:27:27.400782+06:30
3	3	5	0.00	f	2026-06-02 18:27:32.107437+06:30
4	3	7	0.00	f	2026-06-02 18:33:40.383714+06:30
\.


--
-- Data for Name: product_requests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.product_requests (id, warehouse_id, requested_by, batch_code, grade, qty_kg, harvest_date, price_per_kg, status, admin_note, reviewed_by, created_batch_id, created_at, reviewed_at, image_path, description) FROM stdin;
1	1	2	WH-REQ-2026	A	90.00	2026-05-20	58.00	approved	\N	1	5	2026-06-02 12:25:40.021077+06:30	2026-06-02 12:26:45.370926+06:30	\N	\N
2	1	2	DESC-DEMO	B	20.00	2026-05-25	45.00	approved	\N	1	7	2026-06-02 18:14:37.331008+06:30	2026-06-02 18:14:37.867493+06:30	\N	Pure sugarcane jaggery
\.


--
-- Data for Name: promotions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.promotions (id, title, discount_percent, min_qty, start_date, end_date, is_active, created_at) FROM stdin;
1	10% off on 5kg+	15.00	5.00	2026-05-28	2026-07-02	t	2026-06-02 08:24:24.754347+06:30
2	Lucky Draw	20.00	20.00	2026-06-03	2026-07-03	t	2026-06-02 19:17:36.640339+06:30
\.


--
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reviews (id, order_id, customer_id, warehouse_id, rating, comment, created_at) FROM stdin;
\.


--
-- Data for Name: stock_transfers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.stock_transfers (id, from_warehouse_id, to_warehouse_id, batch_id, quantity_kg, status, requested_at, approved_by_admin_id) FROM stdin;
\.


--
-- Data for Name: subscription_plans; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subscription_plans (id, name, duration_months, price, is_active, created_at) FROM stdin;
2	2 Months	2	899.00	t	2026-06-02 16:34:37.5388+06:30
3	6 Months	6	2499.00	t	2026-06-02 16:34:37.5388+06:30
4	1 Year	12	4499.00	t	2026-06-02 16:34:37.5388+06:30
1	1 Month	1	599.00	t	2026-06-02 16:34:37.5388+06:30
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, name, email, password_hash, role, warehouse_id, created_at, phone, address, pincode, payment_pin_hash, pin_reset_code, pin_reset_expires) FROM stdin;
1	Site Admin	admin@jaggery.local	$2b$12$PM.hnxfD4y1pn0ZSV4gjDOpSsG6qRlxPB.a7LrN2rE29vNJjg6lo2	admin	\N	2026-06-02 08:24:24.016597+06:30	\N	\N	\N	\N	\N	\N
2	Warehouse Staff	staff@jaggery.local	$2b$12$p61.gYkioqHnJH.ky8k2qOQZGmR4/SPDd7TAvuuRiAPZdmv4PHz..	warehouse_staff	1	2026-06-02 08:24:24.761394+06:30	09974691655	Ohn Pin Village	Myanmar	$2b$12$jqg2EHrxVfp9Nc/o2AjlDuK565EoERUORIgyF3eSj05ZBYnu1rQkS	\N	\N
3	Mg Mg	customer@jaggery.local	$2b$12$mzjs9uO.TB/Lu7ViMP72uO0QdjH/uWdtUrV22t8yw4irt7qlmhD/C	customer	\N	2026-06-02 08:24:24.761398+06:30	9876543210	Ohn Pin Village	Myanmar	\N	\N	\N
4	Aung Aung	aungaung@gmail.com	$2b$12$2tosiHjCdoKUxezjKQT7i.QiipRMs6UJRU/ozQ3edkYZJqJMalcTu	customer	\N	2026-06-02 20:05:37.774931+06:30	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: warehouse_subscriptions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.warehouse_subscriptions (id, warehouse_id, plan_id, start_date, end_date, price_paid, status, created_at) FROM stdin;
16	1	1	2026-06-02	2026-07-02	599.00	active	2026-06-02 17:29:05.039629+06:30
\.


--
-- Data for Name: warehouses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.warehouses (id, name, location, phone, created_at, pincode, manager_name) FROM stdin;
1	Kolhapur Central	Kolhapur, MH	020-111-2222	2026-06-02 08:24:24.012998+06:30	\N	\N
\.


--
-- Data for Name: wishlist; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.wishlist (id, customer_id, batch_id, added_at) FROM stdin;
1	3	1	2026-06-02 08:55:05.181674+06:30
2	3	5	2026-06-02 18:27:07.338004+06:30
\.


--
-- Name: abandoned_carts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.abandoned_carts_id_seq', 1, false);


--
-- Name: announcements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.announcements_id_seq', 1, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 151, true);


--
-- Name: delivery_charges_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.delivery_charges_id_seq', 1, true);


--
-- Name: jaggery_batches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.jaggery_batches_id_seq', 7, true);


--
-- Name: order_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.order_items_id_seq', 5, true);


--
-- Name: order_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.order_messages_id_seq', 3, true);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.orders_id_seq', 5, true);


--
-- Name: payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payments_id_seq', 13, true);


--
-- Name: price_alerts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.price_alerts_id_seq', 4, true);


--
-- Name: product_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.product_requests_id_seq', 2, true);


--
-- Name: promotions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.promotions_id_seq', 2, true);


--
-- Name: reviews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.reviews_id_seq', 1, false);


--
-- Name: stock_transfers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stock_transfers_id_seq', 1, false);


--
-- Name: subscription_plans_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.subscription_plans_id_seq', 4, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 4, true);


--
-- Name: warehouse_subscriptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.warehouse_subscriptions_id_seq', 16, true);


--
-- Name: warehouses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.warehouses_id_seq', 1, true);


--
-- Name: wishlist_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.wishlist_id_seq', 2, true);


--
-- Name: abandoned_carts abandoned_carts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.abandoned_carts
    ADD CONSTRAINT abandoned_carts_pkey PRIMARY KEY (id);


--
-- Name: announcements announcements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.announcements
    ADD CONSTRAINT announcements_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: delivery_charges delivery_charges_pincode_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.delivery_charges
    ADD CONSTRAINT delivery_charges_pincode_key UNIQUE (pincode);


--
-- Name: delivery_charges delivery_charges_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.delivery_charges
    ADD CONSTRAINT delivery_charges_pkey PRIMARY KEY (id);


--
-- Name: jaggery_batches jaggery_batches_batch_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jaggery_batches
    ADD CONSTRAINT jaggery_batches_batch_id_key UNIQUE (batch_id);


--
-- Name: jaggery_batches jaggery_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jaggery_batches
    ADD CONSTRAINT jaggery_batches_pkey PRIMARY KEY (id);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
-- Name: order_messages order_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_messages
    ADD CONSTRAINT order_messages_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: price_alerts price_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.price_alerts
    ADD CONSTRAINT price_alerts_pkey PRIMARY KEY (id);


--
-- Name: product_requests product_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_requests
    ADD CONSTRAINT product_requests_pkey PRIMARY KEY (id);


--
-- Name: promotions promotions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.promotions
    ADD CONSTRAINT promotions_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_order_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_order_id_key UNIQUE (order_id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: stock_transfers stock_transfers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_transfers
    ADD CONSTRAINT stock_transfers_pkey PRIMARY KEY (id);


--
-- Name: subscription_plans subscription_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscription_plans
    ADD CONSTRAINT subscription_plans_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: warehouse_subscriptions warehouse_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.warehouse_subscriptions
    ADD CONSTRAINT warehouse_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: warehouses warehouses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.warehouses
    ADD CONSTRAINT warehouses_pkey PRIMARY KEY (id);


--
-- Name: wishlist wishlist_customer_id_batch_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.wishlist
    ADD CONSTRAINT wishlist_customer_id_batch_id_key UNIQUE (customer_id, batch_id);


--
-- Name: wishlist wishlist_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.wishlist
    ADD CONSTRAINT wishlist_pkey PRIMARY KEY (id);


--
-- Name: idx_abandoned_customer; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_abandoned_customer ON public.abandoned_carts USING btree (customer_id, created_at);


--
-- Name: idx_announcements_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_announcements_expires ON public.announcements USING btree (expires_at);


--
-- Name: idx_audit_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_user ON public.audit_logs USING btree (user_id, created_at);


--
-- Name: idx_batches_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_batches_active ON public.jaggery_batches USING btree (is_active);


--
-- Name: idx_batches_grade; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_batches_grade ON public.jaggery_batches USING btree (grade);


--
-- Name: idx_batches_harvest; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_batches_harvest ON public.jaggery_batches USING btree (harvest_date);


--
-- Name: idx_batches_warehouse; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_batches_warehouse ON public.jaggery_batches USING btree (warehouse_id);


--
-- Name: idx_order_items_batch; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_order_items_batch ON public.order_items USING btree (batch_pk);


--
-- Name: idx_order_items_order; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_order_items_order ON public.order_items USING btree (order_id);


--
-- Name: idx_order_messages_order; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_order_messages_order ON public.order_messages USING btree (order_id, created_at);


--
-- Name: idx_orders_customer; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_orders_customer ON public.orders USING btree (customer_id);


--
-- Name: idx_orders_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_orders_status ON public.orders USING btree (status);


--
-- Name: idx_orders_warehouse; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_orders_warehouse ON public.orders USING btree (assigned_warehouse_id);


--
-- Name: idx_payments_warehouse; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_payments_warehouse ON public.payments USING btree (warehouse_id, created_at);


--
-- Name: idx_price_alerts_batch; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_price_alerts_batch ON public.price_alerts USING btree (batch_id, is_notified);


--
-- Name: idx_prodreq_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prodreq_status ON public.product_requests USING btree (status);


--
-- Name: idx_prodreq_warehouse; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prodreq_warehouse ON public.product_requests USING btree (warehouse_id, created_at);


--
-- Name: idx_promotions_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_promotions_active ON public.promotions USING btree (is_active, start_date, end_date);


--
-- Name: idx_reviews_warehouse; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_reviews_warehouse ON public.reviews USING btree (warehouse_id);


--
-- Name: idx_transfers_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_transfers_status ON public.stock_transfers USING btree (status);


--
-- Name: idx_users_pincode; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_pincode ON public.users USING btree (pincode);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: idx_users_warehouse_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_warehouse_id ON public.users USING btree (warehouse_id);


--
-- Name: idx_warehouses_pincode; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_warehouses_pincode ON public.warehouses USING btree (pincode);


--
-- Name: idx_whsub_warehouse; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_whsub_warehouse ON public.warehouse_subscriptions USING btree (warehouse_id, end_date);


--
-- Name: idx_wishlist_customer; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_wishlist_customer ON public.wishlist USING btree (customer_id);


--
-- Name: abandoned_carts abandoned_carts_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.abandoned_carts
    ADD CONSTRAINT abandoned_carts_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: announcements announcements_created_by_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.announcements
    ADD CONSTRAINT announcements_created_by_admin_id_fkey FOREIGN KEY (created_by_admin_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: orders fk_orders_promotion; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT fk_orders_promotion FOREIGN KEY (promotion_id) REFERENCES public.promotions(id) ON DELETE SET NULL;


--
-- Name: jaggery_batches jaggery_batches_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jaggery_batches
    ADD CONSTRAINT jaggery_batches_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouses(id) ON DELETE CASCADE;


--
-- Name: order_items order_items_batch_pk_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_batch_pk_fkey FOREIGN KEY (batch_pk) REFERENCES public.jaggery_batches(id) ON DELETE RESTRICT;


--
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_messages order_messages_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_messages
    ADD CONSTRAINT order_messages_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_messages order_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_messages
    ADD CONSTRAINT order_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: orders orders_assigned_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_assigned_warehouse_id_fkey FOREIGN KEY (assigned_warehouse_id) REFERENCES public.warehouses(id) ON DELETE SET NULL;


--
-- Name: orders orders_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: payments payments_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plans(id) ON DELETE SET NULL;


--
-- Name: payments payments_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.warehouse_subscriptions(id) ON DELETE SET NULL;


--
-- Name: payments payments_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouses(id) ON DELETE CASCADE;


--
-- Name: price_alerts price_alerts_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.price_alerts
    ADD CONSTRAINT price_alerts_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.jaggery_batches(id) ON DELETE CASCADE;


--
-- Name: price_alerts price_alerts_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.price_alerts
    ADD CONSTRAINT price_alerts_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: product_requests product_requests_created_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_requests
    ADD CONSTRAINT product_requests_created_batch_id_fkey FOREIGN KEY (created_batch_id) REFERENCES public.jaggery_batches(id) ON DELETE SET NULL;


--
-- Name: product_requests product_requests_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_requests
    ADD CONSTRAINT product_requests_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: product_requests product_requests_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_requests
    ADD CONSTRAINT product_requests_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: product_requests product_requests_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_requests
    ADD CONSTRAINT product_requests_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouses(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouses(id) ON DELETE CASCADE;


--
-- Name: stock_transfers stock_transfers_approved_by_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_transfers
    ADD CONSTRAINT stock_transfers_approved_by_admin_id_fkey FOREIGN KEY (approved_by_admin_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: stock_transfers stock_transfers_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_transfers
    ADD CONSTRAINT stock_transfers_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.jaggery_batches(id) ON DELETE CASCADE;


--
-- Name: stock_transfers stock_transfers_from_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_transfers
    ADD CONSTRAINT stock_transfers_from_warehouse_id_fkey FOREIGN KEY (from_warehouse_id) REFERENCES public.warehouses(id) ON DELETE CASCADE;


--
-- Name: stock_transfers stock_transfers_to_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_transfers
    ADD CONSTRAINT stock_transfers_to_warehouse_id_fkey FOREIGN KEY (to_warehouse_id) REFERENCES public.warehouses(id) ON DELETE CASCADE;


--
-- Name: users users_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouses(id) ON DELETE SET NULL;


--
-- Name: warehouse_subscriptions warehouse_subscriptions_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.warehouse_subscriptions
    ADD CONSTRAINT warehouse_subscriptions_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plans(id) ON DELETE SET NULL;


--
-- Name: warehouse_subscriptions warehouse_subscriptions_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.warehouse_subscriptions
    ADD CONSTRAINT warehouse_subscriptions_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouses(id) ON DELETE CASCADE;


--
-- Name: wishlist wishlist_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.wishlist
    ADD CONSTRAINT wishlist_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.jaggery_batches(id) ON DELETE CASCADE;


--
-- Name: wishlist wishlist_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.wishlist
    ADD CONSTRAINT wishlist_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict PVohtzFfsBLVDJwyZNOmjjxqV6kbywwKdIKO75f0rqXEifPcqTZETuEptIKhgjd

