--
-- PostgreSQL database dump
--

\restrict m2cjONJ0z16GNIkaAbudmuXZVvSTaKBkH3Gl9ZZyyXGSpnvVb5CTcD4NqX8LP6h

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
    charge_amount numeric(10,2) DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT now()
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
    fulfillment character varying(10) DEFAULT 'delivery'::character varying NOT NULL,
    payment_method character varying(20),
    payment_status character varying(20) DEFAULT 'unpaid'::character varying NOT NULL,
    payment_reference character varying(120),
    payment_phone character varying(30),
    customer_seq integer,
    CONSTRAINT orders_fulfillment_chk CHECK (((fulfillment)::text = ANY ((ARRAY['delivery'::character varying, 'pickup'::character varying])::text[]))),
    CONSTRAINT orders_paystatus_chk CHECK (((payment_status)::text = ANY ((ARRAY['unpaid'::character varying, 'paid'::character varying])::text[]))),
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
    avatar_path character varying(255),
    order_count integer DEFAULT 0 NOT NULL,
    pay_otp_hash character varying(255),
    pay_otp_expires timestamp with time zone,
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
    manager_name character varying(120),
    email character varying(160)
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
2	3	[{"qty_kg": 1, "batch_pk": 9}]	2026-06-05 10:06:26.946857+06:30
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
284	2	login	warehouse_staff login	127.0.0.1	2026-06-04 05:29:18.139209+06:30
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
152	1	db_backup	backup_20260603_023050.sql	127.0.0.1	2026-06-03 02:30:50.810759+06:30
153	2	login	warehouse_staff login	127.0.0.1	2026-06-03 02:32:16.426402+06:30
154	3	login	customer login	127.0.0.1	2026-06-03 02:36:05.917594+06:30
155	3	login	customer login	127.0.0.1	2026-06-03 04:38:45.547469+06:30
156	4	login	customer login	127.0.0.1	2026-06-03 04:41:39.534546+06:30
157	4	login	customer login	127.0.0.1	2026-06-03 04:44:15.242692+06:30
158	4	login	customer login	127.0.0.1	2026-06-03 04:46:34.165981+06:30
159	3	login	customer login	127.0.0.1	2026-06-03 04:51:17.058132+06:30
160	3	login	customer login	127.0.0.1	2026-06-03 04:55:33.296608+06:30
161	3	avatar_upload	avatar_3_7d88c152.png	127.0.0.1	2026-06-03 04:55:33.647147+06:30
162	3	avatar_remove	\N	127.0.0.1	2026-06-03 04:55:33.701113+06:30
163	3	avatar_upload	avatar_3_63248e97.jpg	127.0.0.1	2026-06-03 04:56:16.685248+06:30
164	3	login	customer login	127.0.0.1	2026-06-03 05:12:14.222222+06:30
165	3	order_payment	order 7 paid via kpay ref TXN-TEST-1	127.0.0.1	2026-06-03 05:12:15.083773+06:30
166	3	order_payment	order 6 paid via kpay ref transfer	127.0.0.1	2026-06-03 05:13:59.4193+06:30
167	3	order_payment	order 1 paid via kpay ref money	127.0.0.1	2026-06-03 05:14:24.937339+06:30
168	3	login	customer login	127.0.0.1	2026-06-03 05:20:56.813443+06:30
169	3	payment_pin_set	\N	127.0.0.1	2026-06-03 05:20:57.24845+06:30
170	3	order_payment	order 9 paid via kpay ref T1	127.0.0.1	2026-06-03 05:20:57.953672+06:30
171	3	login	customer login	127.0.0.1	2026-06-03 05:27:06.561322+06:30
172	3	order_payment	order 10 paid via kpay ref KPAY123456789	127.0.0.1	2026-06-03 05:27:06.862439+06:30
173	2	login	warehouse_staff login	127.0.0.1	2026-06-03 05:29:15.179012+06:30
174	3	payment_pin_set	\N	127.0.0.1	2026-06-03 05:30:05.451292+06:30
175	3	order_payment	order 4 paid via kpay ref KPAY464578052	127.0.0.1	2026-06-03 05:30:05.480948+06:30
176	3	login	customer login	127.0.0.1	2026-06-03 06:32:30.866053+06:30
177	3	login	customer login	127.0.0.1	2026-06-03 06:35:56.285246+06:30
178	3	login	customer login	127.0.0.1	2026-06-03 06:42:00.189856+06:30
179	3	login	customer login	127.0.0.1	2026-06-03 07:00:00.22816+06:30
180	2	login	warehouse_staff login	127.0.0.1	2026-06-03 07:03:26.748438+06:30
181	2	login	warehouse_staff login	127.0.0.1	2026-06-03 07:03:55.774532+06:30
182	2	login	warehouse_staff login	127.0.0.1	2026-06-03 07:04:49.680951+06:30
183	3	login	customer login	127.0.0.1	2026-06-03 07:05:37.410595+06:30
184	2	login	warehouse_staff login	127.0.0.1	2026-06-03 07:08:56.59349+06:30
185	2	login	warehouse_staff login	127.0.0.1	2026-06-03 07:13:08.800002+06:30
186	2	subscription_payment	1 Month via kpay ref KPAY470789168 (WH#1)	127.0.0.1	2026-06-03 07:13:09.201576+06:30
187	2	subscription_payment	1 Month via kpay ref KPAY470842988 (WH#1)	127.0.0.1	2026-06-03 07:14:03.029446+06:30
188	3	login	customer login	127.0.0.1	2026-06-03 07:14:31.692263+06:30
189	3	order_payment	order 2 paid via kpay ref KPAY470912444	127.0.0.1	2026-06-03 07:15:33.52722+06:30
190	3	order_payment	order 16 paid via kpay ref KPAY472985984	127.0.0.1	2026-06-03 07:49:59.911029+06:30
191	3	login	customer login	127.0.0.1	2026-06-03 08:04:45.109239+06:30
192	3	login	customer login	127.0.0.1	2026-06-03 08:13:52.245763+06:30
193	3	login	customer login	127.0.0.1	2026-06-03 08:28:51.759466+06:30
194	3	login	customer login	127.0.0.1	2026-06-03 08:30:15.51964+06:30
195	3	login	customer login	127.0.0.1	2026-06-03 08:58:40.049727+06:30
196	3	profile_update	\N	127.0.0.1	2026-06-03 09:04:25.061393+06:30
197	3	profile_update	\N	127.0.0.1	2026-06-03 09:04:36.63793+06:30
198	3	login	customer login	127.0.0.1	2026-06-03 09:09:35.220047+06:30
199	1	login	admin login	127.0.0.1	2026-06-03 09:11:12.104351+06:30
200	1	login	admin login	127.0.0.1	2026-06-03 09:41:38.036907+06:30
201	1	login	admin login	127.0.0.1	2026-06-03 10:01:57.767367+06:30
202	1	login	admin login	127.0.0.1	2026-06-03 10:08:39.013911+06:30
203	1	login	admin login	127.0.0.1	2026-06-03 10:10:07.391235+06:30
204	1	login	admin login	127.0.0.1	2026-06-03 10:13:13.184182+06:30
205	1	login	admin login	127.0.0.1	2026-06-03 10:16:30.585582+06:30
206	1	login	admin login	127.0.0.1	2026-06-03 10:20:09.006244+06:30
207	1	login	admin login	127.0.0.1	2026-06-03 10:33:08.299592+06:30
208	1	login	admin login	127.0.0.1	2026-06-03 10:41:41.954543+06:30
209	1	login	admin login	127.0.0.1	2026-06-03 10:50:28.101459+06:30
210	1	login	admin login	127.0.0.1	2026-06-03 13:37:44.784862+06:30
211	1	login	admin login	127.0.0.1	2026-06-03 13:45:59.295135+06:30
212	3	login	customer login	127.0.0.1	2026-06-03 13:52:43.061178+06:30
213	1	login	admin login	127.0.0.1	2026-06-03 14:02:24.212749+06:30
214	1	login	admin login	127.0.0.1	2026-06-03 14:05:56.554872+06:30
215	1	login	admin login	127.0.0.1	2026-06-03 14:10:43.652644+06:30
216	1	login	admin login	127.0.0.1	2026-06-04 01:54:45.625706+06:30
217	3	login	customer login	127.0.0.1	2026-06-04 02:00:10.106544+06:30
218	3	login	customer login	127.0.0.1	2026-06-04 02:05:10.385654+06:30
219	3	login	customer login	127.0.0.1	2026-06-04 02:13:32.332956+06:30
220	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 02:13:33.775442+06:30
221	3	order_payment	order 29 paid via kpay ref T1	127.0.0.1	2026-06-04 02:13:35.435724+06:30
222	3	login	customer login	127.0.0.1	2026-06-04 02:19:07.055921+06:30
223	3	login	customer login	127.0.0.1	2026-06-04 02:25:52.131035+06:30
224	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 02:31:02.929067+06:30
225	2	login	warehouse_staff login	127.0.0.1	2026-06-04 02:32:49.068395+06:30
226	2	subscription_payment	1 Month via kpay ref KPAY540400826 (WH#1)	127.0.0.1	2026-06-04 02:33:20.871362+06:30
227	3	login	customer login	127.0.0.1	2026-06-04 02:33:47.282314+06:30
228	2	login	warehouse_staff login	127.0.0.1	2026-06-04 02:40:14.353484+06:30
229	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-04 02:40:15.069046+06:30
230	2	subscription_payment	1 Month via kpay ref WH1 (WH#1)	127.0.0.1	2026-06-04 02:40:20.151123+06:30
231	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-04 02:41:12.964467+06:30
232	2	login	warehouse_staff login	127.0.0.1	2026-06-04 02:44:39.613958+06:30
233	2	login	warehouse_staff login	127.0.0.1	2026-06-04 02:45:22.12953+06:30
234	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-04 02:45:51.065208+06:30
235	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-04 02:46:02.115975+06:30
236	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-04 02:46:43.000194+06:30
237	2	login	warehouse_staff login	127.0.0.1	2026-06-04 02:46:53.990585+06:30
238	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-04 02:46:55.204184+06:30
239	3	login	customer login	127.0.0.1	2026-06-04 02:46:56.90399+06:30
240	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 02:48:14.036447+06:30
241	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 02:50:44.866629+06:30
242	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 02:51:54.66606+06:30
243	3	login	customer login	127.0.0.1	2026-06-04 02:56:06.18761+06:30
244	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 03:00:29.143056+06:30
245	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 03:09:07.833004+06:30
246	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 03:11:25.634873+06:30
247	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 03:11:34.832511+06:30
248	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 03:11:44.230844+06:30
249	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 03:12:13.058473+06:30
250	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 03:12:17.648218+06:30
251	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 03:15:07.413126+06:30
252	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 03:16:27.173857+06:30
253	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 03:18:02.222081+06:30
254	2	login	warehouse_staff login	127.0.0.1	2026-06-04 03:18:25.533793+06:30
255	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-04 03:19:00.931018+06:30
256	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-04 03:21:54.61142+06:30
257	3	login	customer login	127.0.0.1	2026-06-04 03:22:33.030623+06:30
258	2	login	warehouse_staff login	127.0.0.1	2026-06-04 03:24:24.017574+06:30
259	2	login	warehouse_staff login	127.0.0.1	2026-06-04 03:28:15.779145+06:30
260	2	profile_update	\N	127.0.0.1	2026-06-04 03:34:06.406608+06:30
261	2	profile_update	\N	127.0.0.1	2026-06-04 03:34:26.111041+06:30
262	2	login	warehouse_staff login	127.0.0.1	2026-06-04 03:37:03.30538+06:30
263	2	login	warehouse_staff login	127.0.0.1	2026-06-04 03:46:42.744955+06:30
264	2	batch_removed	Traditional Jaggery (WH#1)	127.0.0.1	2026-06-04 03:46:42.893919+06:30
265	3	login	customer login	127.0.0.1	2026-06-04 03:47:38.795036+06:30
266	1	login	admin login	127.0.0.1	2026-06-04 03:47:39.234515+06:30
267	3	login	customer login	127.0.0.1	2026-06-04 03:48:33.77368+06:30
268	1	login	admin login	127.0.0.1	2026-06-04 03:48:34.285146+06:30
269	2	login	warehouse_staff login	127.0.0.1	2026-06-04 03:55:41.786137+06:30
270	2	login	warehouse_staff login	127.0.0.1	2026-06-04 04:02:33.422433+06:30
271	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-04 04:16:47.576771+06:30
272	2	subscription_payment	1 Month via kpay ref KPAY546614342 (WH#1)	127.0.0.1	2026-06-04 04:16:54.737355+06:30
273	2	product_request	Suagar Jaggery from WH#1	127.0.0.1	2026-06-04 04:22:18.638847+06:30
274	2	login	warehouse_staff login	127.0.0.1	2026-06-04 04:26:13.064447+06:30
275	2	product_request	Black Jaggery from WH#1	127.0.0.1	2026-06-04 04:27:08.56557+06:30
276	2	login	warehouse_staff login	127.0.0.1	2026-06-04 04:31:57.088092+06:30
277	2	login	warehouse_staff login	127.0.0.1	2026-06-04 04:35:39.447827+06:30
278	3	login	customer login	127.0.0.1	2026-06-04 04:40:40.894479+06:30
279	2	login	warehouse_staff login	127.0.0.1	2026-06-04 04:41:09.095662+06:30
280	2	login	warehouse_staff login	127.0.0.1	2026-06-04 04:53:22.060357+06:30
281	3	login	customer login	127.0.0.1	2026-06-04 05:10:37.007315+06:30
282	2	login	warehouse_staff login	127.0.0.1	2026-06-04 05:15:40.622426+06:30
283	2	login	warehouse_staff login	127.0.0.1	2026-06-04 05:28:47.34751+06:30
285	2	profile_update	\N	127.0.0.1	2026-06-04 06:33:13.996271+06:30
286	3	login	customer login	127.0.0.1	2026-06-04 07:29:20.999797+06:30
287	1	login	admin login	127.0.0.1	2026-06-04 07:29:47.765184+06:30
288	3	login	customer login	127.0.0.1	2026-06-04 07:55:22.590937+06:30
289	2	login	warehouse_staff login	127.0.0.1	2026-06-04 07:55:23.082129+06:30
290	3	login	customer login	127.0.0.1	2026-06-04 07:59:38.772357+06:30
291	1	login	admin login	127.0.0.1	2026-06-04 07:59:39.1309+06:30
292	3	login	customer login	127.0.0.1	2026-06-04 08:00:49.388521+06:30
293	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 08:01:33.326039+06:30
294	3	order_payment	order 37 paid via kpay ref KPAY560090988	127.0.0.1	2026-06-04 08:01:38.880795+06:30
295	1	login	admin login	127.0.0.1	2026-06-04 08:01:52.024455+06:30
296	1	login	admin login	127.0.0.1	2026-06-04 08:10:22.793555+06:30
297	3	login	customer login	127.0.0.1	2026-06-04 08:25:50.678688+06:30
298	1	login	admin login	127.0.0.1	2026-06-04 08:25:51.475018+06:30
299	3	login	customer login	127.0.0.1	2026-06-04 08:26:22.737524+06:30
300	1	login	admin login	127.0.0.1	2026-06-04 08:26:23.418851+06:30
301	3	login	customer login	127.0.0.1	2026-06-04 08:26:51.291432+06:30
302	1	login	admin login	127.0.0.1	2026-06-04 08:26:51.87281+06:30
303	3	login	customer login	127.0.0.1	2026-06-04 08:33:23.870952+06:30
304	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-04 08:33:24.734615+06:30
305	3	order_payment	order 47 paid via kpay ref T1	127.0.0.1	2026-06-04 08:33:25.299273+06:30
306	2	login	warehouse_staff login	127.0.0.1	2026-06-04 08:33:25.888038+06:30
307	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-04 08:33:26.414229+06:30
308	2	subscription_payment	1 Month via kpay ref WH1 (WH#1)	127.0.0.1	2026-06-04 08:33:26.90595+06:30
309	3	login	customer login	127.0.0.1	2026-06-04 08:39:55.554995+06:30
310	1	login	admin login	127.0.0.1	2026-06-04 08:39:56.933438+06:30
311	1	login	admin login	127.0.0.1	2026-06-04 08:43:56.707803+06:30
312	1	login	admin login	127.0.0.1	2026-06-04 08:47:40.446452+06:30
313	1	login	admin login	127.0.0.1	2026-06-04 08:57:56.435943+06:30
314	1	login	admin login	127.0.0.1	2026-06-04 08:58:13.583475+06:30
315	1	login	admin login	127.0.0.1	2026-06-04 08:58:33.150783+06:30
316	1	batch_create	MM @ WH#1	127.0.0.1	2026-06-04 09:00:49.319165+06:30
317	1	login	admin login	127.0.0.1	2026-06-04 09:02:22.543307+06:30
318	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:03:37.793713+06:30
319	2	product_request	SuagarA Jaggery from WH#1	127.0.0.1	2026-06-04 09:06:08.636135+06:30
320	1	login	admin login	127.0.0.1	2026-06-04 09:11:19.880566+06:30
321	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:12:52.954675+06:30
322	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:13:05.457465+06:30
323	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:13:06.159327+06:30
324	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:13:21.388338+06:30
325	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:13:53.71618+06:30
326	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:17:15.928831+06:30
327	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:17:32.762184+06:30
328	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:19:19.399538+06:30
329	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:19:40.74102+06:30
330	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:27:43.102919+06:30
331	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:34:11.177854+06:30
332	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:40:15.70996+06:30
333	1	login	admin login	127.0.0.1	2026-06-04 09:40:17.222892+06:30
334	3	login	customer login	127.0.0.1	2026-06-04 09:40:18.365084+06:30
335	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:44:20.956936+06:30
336	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:51:00.650958+06:30
337	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:51:01.467067+06:30
338	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:51:21.875121+06:30
339	2	login	warehouse_staff login	127.0.0.1	2026-06-04 09:56:39.10295+06:30
340	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:01:02.811163+06:30
341	1	login	admin login	127.0.0.1	2026-06-04 10:01:03.344136+06:30
342	1	login	admin login	127.0.0.1	2026-06-04 10:01:20.901099+06:30
343	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:04:45.90413+06:30
344	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:05:09.94535+06:30
345	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:07:17.166637+06:30
346	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:09:35.151587+06:30
347	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:11:57.114136+06:30
348	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:13:01.041394+06:30
349	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:13:57.545526+06:30
350	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:16:23.076451+06:30
351	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:18:25.601214+06:30
352	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:20:21.75765+06:30
353	1	login	admin login	127.0.0.1	2026-06-04 10:22:24.088354+06:30
354	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:24:48.17632+06:30
355	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:25:11.805061+06:30
356	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:25:30.218188+06:30
357	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:25:44.789506+06:30
358	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:32:22.231953+06:30
359	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:32:22.739608+06:30
360	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:32:35.098508+06:30
361	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:41:31.237953+06:30
362	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:41:31.560817+06:30
363	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:48:59.494075+06:30
364	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:50:13.555269+06:30
365	2	login	warehouse_staff login	127.0.0.1	2026-06-04 10:51:41.029902+06:30
366	1	login	admin login	127.0.0.1	2026-06-04 13:32:07.545926+06:30
367	1	login	admin login	127.0.0.1	2026-06-04 13:32:54.291315+06:30
368	1	login	admin login	127.0.0.1	2026-06-04 13:39:25.595798+06:30
369	1	batch_update	MM	127.0.0.1	2026-06-04 13:40:30.916777+06:30
370	1	login	admin login	127.0.0.1	2026-06-04 13:40:36.658715+06:30
371	1	login	admin login	127.0.0.1	2026-06-04 13:44:35.362751+06:30
372	1	login	admin login	127.0.0.1	2026-06-04 13:44:53.448455+06:30
373	1	login	admin login	127.0.0.1	2026-06-04 13:47:57.125941+06:30
374	1	login	admin login	127.0.0.1	2026-06-04 13:53:04.190628+06:30
375	1	login	admin login	127.0.0.1	2026-06-04 13:53:05.105592+06:30
376	1	login	admin login	127.0.0.1	2026-06-04 14:02:57.209192+06:30
377	1	login	admin login	127.0.0.1	2026-06-04 14:09:49.248088+06:30
378	1	login	admin login	127.0.0.1	2026-06-04 14:10:16.7694+06:30
379	1	login	admin login	127.0.0.1	2026-06-04 14:10:17.609766+06:30
380	1	login	admin login	127.0.0.1	2026-06-04 14:15:37.48637+06:30
381	1	login	admin login	127.0.0.1	2026-06-04 14:18:11.206771+06:30
382	1	login	admin login	127.0.0.1	2026-06-04 14:18:28.278064+06:30
383	1	login	admin login	127.0.0.1	2026-06-04 14:18:43.619041+06:30
384	1	login	admin login	127.0.0.1	2026-06-04 14:23:49.904756+06:30
385	2	login	warehouse_staff login	127.0.0.1	2026-06-04 14:25:32.732575+06:30
386	2	login	warehouse_staff login	127.0.0.1	2026-06-04 14:27:10.422243+06:30
387	2	login	warehouse_staff login	127.0.0.1	2026-06-04 14:29:29.959459+06:30
388	2	login	warehouse_staff login	127.0.0.1	2026-06-04 14:31:43.071065+06:30
390	2	login	warehouse_staff login	127.0.0.1	2026-06-04 14:39:51.277556+06:30
395	3	login	customer login	127.0.0.1	2026-06-04 14:57:19.4872+06:30
389	2	login	warehouse_staff login	127.0.0.1	2026-06-04 14:35:54.75431+06:30
391	2	login	warehouse_staff login	127.0.0.1	2026-06-04 14:40:17.633908+06:30
392	2	login	warehouse_staff login	127.0.0.1	2026-06-04 14:44:22.876441+06:30
393	2	login	warehouse_staff login	127.0.0.1	2026-06-04 14:47:49.746119+06:30
394	3	login	customer login	127.0.0.1	2026-06-04 14:48:09.252539+06:30
396	3	login	customer login	127.0.0.1	2026-06-04 15:03:20.519482+06:30
397	3	login	customer login	127.0.0.1	2026-06-04 15:05:48.82839+06:30
398	3	login	customer login	127.0.0.1	2026-06-04 15:10:16.025772+06:30
399	3	login	customer login	127.0.0.1	2026-06-04 15:15:48.603057+06:30
400	1	login	admin login	127.0.0.1	2026-06-04 15:21:48.665262+06:30
401	3	login	customer login	127.0.0.1	2026-06-04 15:28:39.949715+06:30
402	3	login	customer login	127.0.0.1	2026-06-04 15:29:08.614915+06:30
403	3	login	customer login	127.0.0.1	2026-06-04 15:29:09.298671+06:30
404	3	login	customer login	127.0.0.1	2026-06-04 15:33:58.910586+06:30
405	3	login	customer login	127.0.0.1	2026-06-04 15:36:42.207665+06:30
406	3	login	customer login	127.0.0.1	2026-06-04 15:37:07.245631+06:30
407	3	login	customer login	127.0.0.1	2026-06-04 15:40:00.823044+06:30
408	3	login	customer login	127.0.0.1	2026-06-04 15:42:50.868306+06:30
409	3	login	customer login	127.0.0.1	2026-06-04 15:43:59.95722+06:30
410	3	login	customer login	127.0.0.1	2026-06-04 15:45:43.668797+06:30
411	3	login	customer login	127.0.0.1	2026-06-04 15:46:56.124721+06:30
412	3	login	customer login	127.0.0.1	2026-06-04 15:46:57.100156+06:30
413	3	login	customer login	127.0.0.1	2026-06-04 15:48:17.640221+06:30
414	3	login	customer login	127.0.0.1	2026-06-04 15:49:35.955901+06:30
415	3	login	customer login	127.0.0.1	2026-06-04 15:52:38.506256+06:30
416	3	login	customer login	127.0.0.1	2026-06-04 15:55:56.422545+06:30
417	3	login	customer login	127.0.0.1	2026-06-04 15:55:57.367923+06:30
418	3	login	customer login	127.0.0.1	2026-06-04 15:59:24.118685+06:30
419	3	login	customer login	127.0.0.1	2026-06-04 16:02:29.916391+06:30
420	3	login	customer login	127.0.0.1	2026-06-04 16:02:30.432987+06:30
421	3	login	customer login	127.0.0.1	2026-06-04 16:11:29.956501+06:30
422	3	login	customer login	127.0.0.1	2026-06-04 16:13:41.744053+06:30
423	3	login	customer login	127.0.0.1	2026-06-04 16:16:31.905595+06:30
424	3	login	customer login	127.0.0.1	2026-06-04 16:18:55.827829+06:30
425	1	login	admin login	127.0.0.1	2026-06-04 16:20:09.416564+06:30
426	1	login	admin login	127.0.0.1	2026-06-04 16:21:55.798296+06:30
427	1	login	admin login	127.0.0.1	2026-06-04 16:31:20.593602+06:30
428	1	login	admin login	127.0.0.1	2026-06-04 16:33:40.312982+06:30
429	1	login	admin login	127.0.0.1	2026-06-04 16:36:55.696157+06:30
430	1	login	admin login	127.0.0.1	2026-06-04 16:36:56.690144+06:30
431	1	login	admin login	127.0.0.1	2026-06-04 16:39:00.269314+06:30
432	1	login	admin login	127.0.0.1	2026-06-04 16:39:00.795094+06:30
433	1	login	admin login	127.0.0.1	2026-06-04 16:39:58.783504+06:30
434	1	login	admin login	127.0.0.1	2026-06-04 16:41:22.758392+06:30
435	1	login	admin login	127.0.0.1	2026-06-04 16:42:48.137082+06:30
436	1	login	admin login	127.0.0.1	2026-06-04 16:44:05.487736+06:30
437	1	login	admin login	127.0.0.1	2026-06-04 16:44:53.764973+06:30
438	1	login	admin login	127.0.0.1	2026-06-04 16:47:05.649108+06:30
439	1	login	admin login	127.0.0.1	2026-06-05 04:00:40.734013+06:30
440	1	login	admin login	127.0.0.1	2026-06-05 04:11:10.700128+06:30
441	1	login	admin login	127.0.0.1	2026-06-05 04:18:45.438899+06:30
442	1	login	admin login	127.0.0.1	2026-06-05 04:19:45.084908+06:30
443	1	login	admin login	127.0.0.1	2026-06-05 04:26:43.622183+06:30
444	1	login	admin login	127.0.0.1	2026-06-05 04:40:15.120738+06:30
445	1	login	admin login	127.0.0.1	2026-06-05 04:44:21.381586+06:30
446	1	login	admin login	127.0.0.1	2026-06-05 04:48:40.573536+06:30
447	1	login	admin login	127.0.0.1	2026-06-05 04:48:41.09679+06:30
448	1	login	admin login	127.0.0.1	2026-06-05 04:55:07.536586+06:30
449	1	login	admin login	127.0.0.1	2026-06-05 04:57:52.128046+06:30
450	1	login	admin login	127.0.0.1	2026-06-05 04:59:58.944253+06:30
451	1	login	admin login	127.0.0.1	2026-06-05 04:59:59.400896+06:30
452	1	login	admin login	127.0.0.1	2026-06-05 05:00:40.187571+06:30
453	1	login	admin login	127.0.0.1	2026-06-05 05:03:17.544283+06:30
454	1	login	admin login	127.0.0.1	2026-06-05 05:07:45.560605+06:30
455	1	login	admin login	127.0.0.1	2026-06-05 05:09:22.832503+06:30
456	1	login	admin login	127.0.0.1	2026-06-05 05:11:03.912528+06:30
457	1	login	admin login	127.0.0.1	2026-06-05 05:12:00.913212+06:30
458	1	login	admin login	127.0.0.1	2026-06-05 05:15:59.452622+06:30
459	1	login	admin login	127.0.0.1	2026-06-05 06:41:26.057037+06:30
460	1	login	admin login	127.0.0.1	2026-06-05 06:48:10.296813+06:30
461	1	login	admin login	127.0.0.1	2026-06-05 06:51:08.102604+06:30
462	1	login	admin login	127.0.0.1	2026-06-05 06:54:36.520426+06:30
463	1	login	admin login	127.0.0.1	2026-06-05 06:59:39.423833+06:30
464	1	login	admin login	127.0.0.1	2026-06-05 06:59:40.803285+06:30
465	1	login	admin login	127.0.0.1	2026-06-05 07:02:21.182428+06:30
466	1	login	admin login	127.0.0.1	2026-06-05 07:10:26.488849+06:30
467	1	login	admin login	127.0.0.1	2026-06-05 07:10:27.391301+06:30
468	2	login	warehouse_staff login	127.0.0.1	2026-06-05 07:11:23.584643+06:30
469	2	product_request	Suagar Jaggery from WH#1	127.0.0.1	2026-06-05 07:12:17.558323+06:30
470	1	login	admin login	127.0.0.1	2026-06-05 07:12:46.854075+06:30
471	1	login	admin login	127.0.0.1	2026-06-05 07:15:54.554466+06:30
472	2	login	warehouse_staff login	127.0.0.1	2026-06-05 07:15:55.70418+06:30
473	1	login	admin login	127.0.0.1	2026-06-05 07:16:43.593158+06:30
474	1	login	admin login	127.0.0.1	2026-06-05 07:22:27.259945+06:30
475	1	product_request_rejected	SuagarA Jaggery	127.0.0.1	2026-06-05 07:24:00.698104+06:30
476	1	login	admin login	127.0.0.1	2026-06-05 07:28:54.36706+06:30
477	1	login	admin login	127.0.0.1	2026-06-05 07:29:13.269837+06:30
478	1	login	admin login	127.0.0.1	2026-06-05 07:32:48.659262+06:30
479	1	login	admin login	127.0.0.1	2026-06-05 07:34:02.003057+06:30
480	1	login	admin login	127.0.0.1	2026-06-05 07:37:02.186008+06:30
481	2	login	warehouse_staff login	127.0.0.1	2026-06-05 07:39:27.750677+06:30
482	1	login	admin login	127.0.0.1	2026-06-05 07:40:37.807637+06:30
483	2	product_request	Suagar Jaggery from WH#1	127.0.0.1	2026-06-05 07:40:57.426858+06:30
484	1	login	admin login	127.0.0.1	2026-06-05 07:41:30.958161+06:30
485	2	login	warehouse_staff login	127.0.0.1	2026-06-05 07:42:40.030468+06:30
486	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-05 07:43:00.139791+06:30
487	2	subscription_payment	6 Months via kpay ref KPAY645383125 (WH#1)	127.0.0.1	2026-06-05 07:43:04.186787+06:30
488	1	login	admin login	127.0.0.1	2026-06-05 07:43:19.036888+06:30
489	1	login	admin login	127.0.0.1	2026-06-05 07:48:38.739149+06:30
490	1	login	admin login	127.0.0.1	2026-06-05 07:51:34.473896+06:30
491	1	login	admin login	127.0.0.1	2026-06-05 07:56:07.046295+06:30
492	1	login	admin login	127.0.0.1	2026-06-05 07:58:20.399532+06:30
493	1	login	admin login	127.0.0.1	2026-06-05 08:01:25.739494+06:30
494	1	login	admin login	127.0.0.1	2026-06-05 08:05:14.824881+06:30
495	1	login	admin login	127.0.0.1	2026-06-05 08:08:16.716263+06:30
498	1	login	admin login	127.0.0.1	2026-06-05 08:13:41.769055+06:30
496	2	login	warehouse_staff login	127.0.0.1	2026-06-05 08:09:13.653584+06:30
497	2	login	warehouse_staff login	127.0.0.1	2026-06-05 08:13:38.932583+06:30
499	2	login	warehouse_staff login	127.0.0.1	2026-06-05 08:15:36.884612+06:30
500	1	login	admin login	127.0.0.1	2026-06-05 08:17:22.496525+06:30
501	2	login	warehouse_staff login	127.0.0.1	2026-06-05 08:18:41.681516+06:30
502	1	login	admin login	127.0.0.1	2026-06-05 08:18:42.204212+06:30
503	1	login	admin login	127.0.0.1	2026-06-05 08:19:02.923902+06:30
504	1	login	admin login	127.0.0.1	2026-06-05 08:25:05.040023+06:30
505	1	login	admin login	127.0.0.1	2026-06-05 08:28:09.163314+06:30
506	2	login	warehouse_staff login	127.0.0.1	2026-06-05 08:28:09.721434+06:30
507	1	login	admin login	127.0.0.1	2026-06-05 08:31:47.737266+06:30
508	2	login	warehouse_staff login	127.0.0.1	2026-06-05 08:31:48.791956+06:30
509	1	login	admin login	127.0.0.1	2026-06-05 08:36:19.235728+06:30
510	2	login	warehouse_staff login	127.0.0.1	2026-06-05 08:36:20.695439+06:30
511	1	login	admin login	127.0.0.1	2026-06-05 08:36:21.795547+06:30
512	2	login	warehouse_staff login	127.0.0.1	2026-06-05 08:43:56.34744+06:30
513	3	login	customer login	127.0.0.1	2026-06-05 08:47:09.690549+06:30
514	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-05 08:48:14.049139+06:30
515	3	order_payment	order 64 paid via kpay ref KPAY649279159	127.0.0.1	2026-06-05 08:48:22.422607+06:30
516	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-05 08:51:54.914731+06:30
517	3	order_payment	order 62 paid via kpay ref KPAY649508522	127.0.0.1	2026-06-05 08:51:58.423554+06:30
518	2	login	warehouse_staff login	127.0.0.1	2026-06-05 08:59:13.526489+06:30
519	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-05 09:00:57.08076+06:30
520	2	subscription_payment	1 Month via kpay ref KPAY650060647 (WH#1)	127.0.0.1	2026-06-05 09:01:01.625604+06:30
521	2	product_request	Suagar Jaggery from WH#1	127.0.0.1	2026-06-05 09:01:51.631093+06:30
522	1	login	admin login	127.0.0.1	2026-06-05 09:02:02.282633+06:30
523	1	product_request_approved	Suagar Jaggery -> batch #10	127.0.0.1	2026-06-05 09:02:32.582555+06:30
524	3	login	customer login	127.0.0.1	2026-06-05 09:02:41.156798+06:30
525	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-05 09:04:17.884841+06:30
526	3	order_payment	order 65 paid via wavepay ref WAVE650254747	127.0.0.1	2026-06-05 09:04:24.24748+06:30
527	1	login	admin login	127.0.0.1	2026-06-05 09:05:18.482964+06:30
528	3	login	customer login	127.0.0.1	2026-06-05 09:14:16.082087+06:30
529	1	login	admin login	127.0.0.1	2026-06-05 09:25:31.355124+06:30
530	1	login	admin login	127.0.0.1	2026-06-05 09:25:49.138025+06:30
531	1	login	admin login	127.0.0.1	2026-06-05 09:32:19.600816+06:30
532	1	login	admin login	127.0.0.1	2026-06-05 09:32:21.17302+06:30
533	1	login	admin login	127.0.0.1	2026-06-05 09:32:32.487252+06:30
534	3	login	customer login	127.0.0.1	2026-06-05 09:58:22.450497+06:30
535	3	login	customer login	127.0.0.1	2026-06-05 09:58:48.140972+06:30
536	1	login	admin login	127.0.0.1	2026-06-05 10:00:52.920952+06:30
537	2	login	warehouse_staff login	127.0.0.1	2026-06-05 10:00:54.208253+06:30
538	2	product_request	TEST-CAT-10 from WH#1	127.0.0.1	2026-06-05 10:00:54.460181+06:30
539	1	login	admin login	127.0.0.1	2026-06-05 10:03:10.480566+06:30
540	1	product_request_approved	TEST-CAT-10 -> batch #11	127.0.0.1	2026-06-05 10:03:10.721623+06:30
541	3	login	customer login	127.0.0.1	2026-06-05 10:03:11.477272+06:30
542	1	login	admin login	127.0.0.1	2026-06-05 10:03:34.28823+06:30
543	1	batch_delete	TEST-CAT-10	127.0.0.1	2026-06-05 10:03:34.677485+06:30
544	1	login	admin login	127.0.0.1	2026-06-05 10:06:34.254155+06:30
545	1	batch_create	MMm @ WH#1	127.0.0.1	2026-06-05 10:07:38.252752+06:30
546	3	login	customer login	127.0.0.1	2026-06-05 10:07:53.372974+06:30
547	3	login	customer login	127.0.0.1	2026-06-05 10:10:05.806979+06:30
548	1	login	admin login	127.0.0.1	2026-06-05 10:10:56.048915+06:30
549	1	batch_create	Muuny @ WH#1	127.0.0.1	2026-06-05 10:11:38.626233+06:30
550	3	login	customer login	127.0.0.1	2026-06-05 10:12:43.186448+06:30
551	3	login	customer login	127.0.0.1	2026-06-05 10:20:07.273336+06:30
552	1	login	admin login	127.0.0.1	2026-06-05 10:20:57.394171+06:30
553	3	login	customer login	127.0.0.1	2026-06-05 10:21:32.566069+06:30
554	3	login	customer login	127.0.0.1	2026-06-05 10:27:49.682623+06:30
555	1	login	admin login	127.0.0.1	2026-06-05 10:28:32.119755+06:30
556	3	login	customer login	127.0.0.1	2026-06-05 10:29:55.042186+06:30
557	1	login	admin login	127.0.0.1	2026-06-05 10:30:57.192503+06:30
558	1	batch_create	DEMO-LIVE-NOTIF @ WH#1	127.0.0.1	2026-06-05 10:30:57.376686+06:30
559	1	login	admin login	127.0.0.1	2026-06-05 10:32:43.754562+06:30
560	1	batch_delete	DEMO-LIVE-NOTIF	127.0.0.1	2026-06-05 10:32:44.006495+06:30
561	1	login	admin login	127.0.0.1	2026-06-05 10:37:59.31814+06:30
562	1	login	admin login	127.0.0.1	2026-06-05 10:40:27.303165+06:30
563	1	batch_create	Honey @ WH#1	127.0.0.1	2026-06-05 10:41:09.448697+06:30
564	3	login	customer login	127.0.0.1	2026-06-05 10:41:17.592283+06:30
565	1	login	admin login	127.0.0.1	2026-06-05 10:41:26.622769+06:30
566	1	login	admin login	127.0.0.1	2026-06-05 10:42:07.974014+06:30
567	1	batch_create	Sony @ WH#1	127.0.0.1	2026-06-05 10:43:01.905059+06:30
568	3	login	customer login	127.0.0.1	2026-06-05 10:43:14.64631+06:30
569	1	login	admin login	127.0.0.1	2026-06-05 10:45:44.738841+06:30
570	3	login	customer login	127.0.0.1	2026-06-05 10:47:44.173058+06:30
571	1	login	admin login	127.0.0.1	2026-06-05 10:47:57.700957+06:30
572	1	batch_create	DEMO-POPUP @ WH#1	127.0.0.1	2026-06-05 10:47:57.903995+06:30
573	1	login	admin login	127.0.0.1	2026-06-05 10:48:56.970774+06:30
574	1	batch_delete	DEMO-POPUP	127.0.0.1	2026-06-05 10:48:57.070987+06:30
575	1	login	admin login	127.0.0.1	2026-06-05 10:50:31.581168+06:30
576	1	batch_create	Bunny @ WH#1	127.0.0.1	2026-06-05 10:50:58.633775+06:30
577	3	login	customer login	127.0.0.1	2026-06-05 10:51:07.313404+06:30
578	1	login	admin login	127.0.0.1	2026-06-05 10:57:04.627303+06:30
579	3	login	customer login	127.0.0.1	2026-06-05 10:57:38.219872+06:30
580	3	login	customer login	127.0.0.1	2026-06-05 11:00:51.291093+06:30
581	1	login	admin login	127.0.0.1	2026-06-05 11:01:03.357136+06:30
582	1	batch_create	DEMO-OBVIOUS @ WH#1	127.0.0.1	2026-06-05 11:01:03.489941+06:30
583	1	login	admin login	127.0.0.1	2026-06-05 11:02:22.084124+06:30
584	1	batch_delete	DEMO-OBVIOUS	127.0.0.1	2026-06-05 11:02:22.239261+06:30
585	3	login	customer login	127.0.0.1	2026-06-06 16:10:42.32428+06:30
586	1	login	admin login	127.0.0.1	2026-06-06 16:11:24.830951+06:30
587	1	product_request_rejected	Suagar Jaggery	127.0.0.1	2026-06-06 16:11:42.965784+06:30
588	1	batch_create	Bunn @ WH#1	127.0.0.1	2026-06-06 16:12:06.291969+06:30
589	3	login	customer login	127.0.0.1	2026-06-06 16:12:23.453778+06:30
590	3	login	customer login	127.0.0.1	2026-06-06 16:21:02.614037+06:30
591	1	login	admin login	127.0.0.1	2026-06-06 16:21:15.926618+06:30
592	1	batch_create	DEMO-ALARM-1 @ WH#1	127.0.0.1	2026-06-06 16:21:16.27477+06:30
593	1	login	admin login	127.0.0.1	2026-06-06 16:21:38.398624+06:30
594	1	batch_create	DEMO-ALARM-2 @ WH#1	127.0.0.1	2026-06-06 16:21:38.760366+06:30
595	1	login	admin login	127.0.0.1	2026-06-06 16:23:49.979501+06:30
596	1	batch_create	DEMO-ALARM-3 @ WH#1	127.0.0.1	2026-06-06 16:23:50.214159+06:30
597	1	login	admin login	127.0.0.1	2026-06-06 16:24:11.308023+06:30
603	1	batch_delete	DEMO-ALARM-6	127.0.0.1	2026-06-06 16:25:35.74863+06:30
607	1	batch_delete	DEMO-ALARM-3	127.0.0.1	2026-06-06 16:25:35.978851+06:30
620	1	login	admin login	127.0.0.1	2026-06-06 16:51:43.185337+06:30
622	1	login	admin login	127.0.0.1	2026-06-06 17:00:59.144241+06:30
625	1	login	admin login	127.0.0.1	2026-06-06 17:02:03.261937+06:30
630	1	batch_delete	DEMO-WH-CAT	127.0.0.1	2026-06-06 17:03:20.694855+06:30
634	3	login	customer login	127.0.0.1	2026-06-06 17:13:44.004658+06:30
637	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:15:17.918363+06:30
598	1	batch_create	DEMO-ALARM-4 @ WH#1	127.0.0.1	2026-06-06 16:24:11.563177+06:30
600	1	batch_create	DEMO-ALARM-5 @ WH#1	127.0.0.1	2026-06-06 16:24:49.363139+06:30
605	1	batch_delete	DEMO-ALARM-2	127.0.0.1	2026-06-06 16:25:35.87903+06:30
610	3	login	customer login	127.0.0.1	2026-06-06 16:30:14.924436+06:30
621	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:00:41.421839+06:30
624	1	plan_create	DEMO Plan 3mo	127.0.0.1	2026-06-06 17:00:59.526908+06:30
628	1	login	admin login	127.0.0.1	2026-06-06 17:03:20.412296+06:30
635	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:13:58.640381+06:30
599	1	login	admin login	127.0.0.1	2026-06-06 16:24:49.093234+06:30
601	1	batch_create	DEMO-ALARM-6 @ WH#1	127.0.0.1	2026-06-06 16:24:49.427661+06:30
606	1	batch_delete	DEMO-ALARM-5	127.0.0.1	2026-06-06 16:25:35.931014+06:30
609	1	login	admin login	127.0.0.1	2026-06-06 16:26:57.386423+06:30
611	3	login	customer login	127.0.0.1	2026-06-06 16:30:37.085798+06:30
612	1	login	admin login	127.0.0.1	2026-06-06 16:31:02.512374+06:30
613	1	batch_create	MMl @ WH#1	127.0.0.1	2026-06-06 16:31:32.518204+06:30
614	1	login	admin login	127.0.0.1	2026-06-06 16:44:33.034141+06:30
623	1	batch_create	DEMO-WH-CAT @ WH#1	127.0.0.1	2026-06-06 17:00:59.442092+06:30
626	1	batch_create	DEMO-WH-CAT-2 @ WH#1	127.0.0.1	2026-06-06 17:02:03.509698+06:30
631	1	plan_delete	DEMO Plan 3mo	127.0.0.1	2026-06-06 17:03:20.89529+06:30
636	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:14:53.70232+06:30
645	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:32:26.009776+06:30
602	1	login	admin login	127.0.0.1	2026-06-06 16:25:35.391156+06:30
604	1	batch_delete	DEMO-ALARM-4	127.0.0.1	2026-06-06 16:25:35.826786+06:30
608	1	batch_delete	DEMO-ALARM-1	127.0.0.1	2026-06-06 16:25:36.014282+06:30
615	1	batch_create	Muu @ WH#1	127.0.0.1	2026-06-06 16:44:59.728627+06:30
616	3	login	customer login	127.0.0.1	2026-06-06 16:45:07.801358+06:30
617	3	login	customer login	127.0.0.1	2026-06-06 16:48:02.591585+06:30
618	3	login	customer login	127.0.0.1	2026-06-06 16:49:10.140463+06:30
619	2	login	warehouse_staff login	127.0.0.1	2026-06-06 16:50:54.238976+06:30
627	1	plan_create	DEMO Plan 9mo	127.0.0.1	2026-06-06 17:02:03.574068+06:30
629	1	batch_delete	DEMO-WH-CAT-2	127.0.0.1	2026-06-06 17:03:20.644826+06:30
632	1	plan_delete	DEMO Plan 9mo	127.0.0.1	2026-06-06 17:03:20.955939+06:30
633	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:13:22.634563+06:30
638	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:17:44.103448+06:30
639	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:19:13.847985+06:30
640	3	login	customer login	127.0.0.1	2026-06-06 17:19:51.439038+06:30
641	3	login	customer login	127.0.0.1	2026-06-06 17:25:01.570149+06:30
642	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:25:18.541181+06:30
643	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:27:01.577103+06:30
644	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:29:04.402416+06:30
646	3	login	customer login	127.0.0.1	2026-06-06 17:32:51.897909+06:30
647	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:33:17.096349+06:30
648	3	login	customer login	127.0.0.1	2026-06-06 17:33:31.468544+06:30
649	3	login	customer login	127.0.0.1	2026-06-06 17:38:41.119281+06:30
650	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:38:52.001445+06:30
651	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:39:40.975279+06:30
652	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:43:09.01688+06:30
653	3	login	customer login	127.0.0.1	2026-06-06 17:43:33.35817+06:30
654	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:44:04.121277+06:30
655	1	login	admin login	127.0.0.1	2026-06-06 17:44:38.552872+06:30
656	1	batch_create	baby @ WH#1	127.0.0.1	2026-06-06 17:45:08.23825+06:30
657	3	login	customer login	127.0.0.1	2026-06-06 17:45:17.251199+06:30
658	1	login	admin login	127.0.0.1	2026-06-06 17:45:53.380457+06:30
659	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:46:11.93665+06:30
660	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:46:41.912438+06:30
661	2	login	warehouse_staff login	127.0.0.1	2026-06-06 17:56:29.268152+06:30
662	1	login	admin login	127.0.0.1	2026-06-06 17:56:43.621307+06:30
663	1	batch_create	DEMO-WH-NEWCAT @ WH#1	127.0.0.1	2026-06-06 17:56:43.882203+06:30
664	1	login	admin login	127.0.0.1	2026-06-06 17:59:13.433235+06:30
665	1	login	admin login	127.0.0.1	2026-06-06 18:00:19.584513+06:30
666	1	batch_delete	DEMO-WH-NEWCAT	127.0.0.1	2026-06-06 18:00:20.058089+06:30
667	2	login	warehouse_staff login	127.0.0.1	2026-06-06 18:01:35.639812+06:30
668	1	login	admin login	127.0.0.1	2026-06-06 18:01:54.821618+06:30
669	1	batch_create	DEMO-WH-NEWCAT @ WH#1	127.0.0.1	2026-06-06 18:01:55.09128+06:30
670	1	login	admin login	127.0.0.1	2026-06-06 18:02:31.17019+06:30
671	1	batch_delete	DEMO-WH-NEWCAT	127.0.0.1	2026-06-06 18:02:31.507644+06:30
672	1	login	admin login	127.0.0.1	2026-06-06 18:06:43.872978+06:30
673	1	batch_create	Muunyr @ WH#1	127.0.0.1	2026-06-06 18:07:20.830634+06:30
674	2	login	warehouse_staff login	127.0.0.1	2026-06-06 18:07:30.545012+06:30
675	1	login	admin login	127.0.0.1	2026-06-06 18:13:02.731297+06:30
676	2	login	warehouse_staff login	127.0.0.1	2026-06-06 18:13:25.872037+06:30
677	2	product_request	REQ-DEMO-PROD from WH#1	127.0.0.1	2026-06-06 18:13:26.24961+06:30
678	2	login	warehouse_staff login	127.0.0.1	2026-06-06 18:21:13.584177+06:30
679	2	product_request	Suagar Jaggery7 from WH#1	127.0.0.1	2026-06-06 18:22:02.403538+06:30
680	2	subscription_otp_requested	s***@jaggery.local	127.0.0.1	2026-06-06 18:22:17.7471+06:30
681	2	subscription_payment	1 Month via kpay ref KPAY770140043 (WH#1)	127.0.0.1	2026-06-06 18:22:21.105502+06:30
682	3	login	customer login	127.0.0.1	2026-06-06 18:23:25.485801+06:30
683	1	login	admin login	127.0.0.1	2026-06-06 18:28:45.350008+06:30
684	1	login	admin login	127.0.0.1	2026-06-06 18:33:09.504823+06:30
685	3	login	customer login	127.0.0.1	2026-06-06 18:33:31.37594+06:30
686	2	login	warehouse_staff login	127.0.0.1	2026-06-06 18:33:58.033459+06:30
687	2	login	warehouse_staff login	127.0.0.1	2026-06-06 18:39:40.011204+06:30
688	2	login	warehouse_staff login	127.0.0.1	2026-06-06 18:47:03.992095+06:30
689	2	login	warehouse_staff login	127.0.0.1	2026-06-06 18:49:12.357162+06:30
690	1	login	admin login	127.0.0.1	2026-06-06 18:50:09.771679+06:30
691	3	login	customer login	127.0.0.1	2026-06-06 18:51:56.201836+06:30
692	3	login	customer login	127.0.0.1	2026-06-06 18:55:01.997184+06:30
693	3	login	customer login	127.0.0.1	2026-06-06 19:02:08.335592+06:30
694	3	login	customer login	127.0.0.1	2026-06-06 19:05:41.035564+06:30
695	3	login	customer login	127.0.0.1	2026-06-06 19:11:30.741147+06:30
696	3	login	customer login	127.0.0.1	2026-06-06 19:20:41.285218+06:30
697	2	login	warehouse_staff login	127.0.0.1	2026-06-06 19:20:59.772425+06:30
698	3	payment_otp_requested	c***@jaggery.local	127.0.0.1	2026-06-06 19:24:06.078631+06:30
699	3	order_payment	order 61 paid via kpay ref KPAY773842538	127.0.0.1	2026-06-06 19:24:09.390997+06:30
700	1	login	admin login	127.0.0.1	2026-06-06 19:32:04.738705+06:30
701	1	login	admin login	127.0.0.1	2026-06-06 19:35:41.673284+06:30
702	1	login	admin login	127.0.0.1	2026-06-06 19:41:40.702234+06:30
703	1	login	admin login	127.0.0.1	2026-06-06 19:57:54.547245+06:30
\.


--
-- Data for Name: delivery_charges; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.delivery_charges (id, pincode, charge_amount, created_at) FROM stdin;
3	Sittwe	66.00	2026-06-05 11:28:49.257425
4	Myitkyina	33.00	2026-06-05 11:28:49.257425
2	Meiktila	55.00	2026-06-05 11:28:49.257425
\.


--
-- Data for Name: jaggery_batches; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.jaggery_batches (id, warehouse_id, batch_id, grade, qty_kg, harvest_date, price_per_kg, certificate_path, created_at, is_active, image_path, description) FROM stdin;
34	1	Muunyr	A	50.00	2026-06-08	35.00	\N	2026-06-06 18:07:20.832497+06:30	t	\N	Ingredients: lemon\n\nEffectiveness: release the tension
4	1	Organic Jaggery Powder	A	75.00	2026-05-15	52.00	\N	2026-06-02 09:53:31.806736+06:30	t	\N	\N
7	1	Coconut Jaggery	B	7.50	2026-05-25	45.00	\N	2026-06-02 18:14:37.87327+06:30	t	\N	Pure sugarcane jaggery
5	1	Palm Jaggery	A	89.00	2026-05-20	58.00	\N	2026-06-02 12:26:45.380589+06:30	t	\N	\N
6	1	Economy Jaggery	D	38.50	2026-05-15	35.00	\N	2026-06-02 17:50:54.039923+06:30	t	\N	\N
10	1	Suagar Jaggery	A	50.00	2026-06-06	35.00	\N	2026-06-05 09:02:32.528451+06:30	t	\N	Ingredients: sugar\n\nEffectiveness: release the tension
9	1	MM	A	48.00	2026-06-30	35.00	\N	2026-06-04 09:00:49.327596+06:30	t	\N	Ingredients: sugar\n\nEffectiveness: release the tension
12	1	MMm	A	50.00	2026-06-06	35.00	\N	2026-06-05 10:07:38.254214+06:30	t	\N	Ingredients: sugar\n\nEffectiveness: release the tension
2	1	Pure Cane Jaggery Block	B	40.00	2026-04-03	45.00	\N	2026-06-02 08:24:24.744407+06:30	t	\N	\N
8	1	Aged Jaggery (demo)	B	25.00	2025-05-15	40.00	\N	2026-06-04 11:30:36.211955+06:30	t	\N	\N
1	1	Premium Sugarcane Jaggery	A	120.00	2026-05-03	60.00	\N	2026-06-02 08:24:24.744404+06:30	t	batch_JAG-2026-001_0504a9f2.png	Made from 100% organic sugarcane juice, slow-boiled in traditional iron woks with no chemicals or refined sugar. Rich in iron, magnesium and potassium. Boosts immunity, aids digestion, cleanses the liver, and gives natural sustained energy. Great as a healthy sweetener for tea, sweets and daily cooking.
13	1	Muuny	A	50.00	2026-06-24	35.00	\N	2026-06-05 10:11:38.627748+06:30	t	\N	Ingredients: sugar\n\nEffectiveness: release the tension
15	1	Honey	C	50.00	2026-06-06	35.00	\N	2026-06-05 10:41:09.451143+06:30	t	\N	Ingredients: sugar\n\nEffectiveness: release the tension
16	1	Sony	A	50.00	2026-06-06	35.00	\N	2026-06-05 10:43:01.919829+06:30	t	\N	Ingredients: lemon\n\nEffectiveness: release the tension
18	1	Bunny	A	50.00	2026-06-30	35.00	\N	2026-06-05 10:50:58.635243+06:30	t	\N	Ingredients: lemon\n\nEffectiveness: release the tension
20	1	Bunn	A	50.00	2026-06-07	35.00	\N	2026-06-06 16:12:06.29852+06:30	t	\N	Ingredients: lemon\n\nEffectiveness: release the tension
27	1	MMl	A	50.00	2026-06-07	35.00	\N	2026-06-06 16:31:32.519543+06:30	t	\N	Ingredients: lemon\n\nEffectiveness: release the tension
28	1	Muu	A	50.00	2026-06-07	35.00	\N	2026-06-06 16:44:59.737332+06:30	t	\N	Ingredients: lemon\n\nEffectiveness: release the tension
31	1	baby	A	50.00	2026-06-08	35.00	\N	2026-06-06 17:45:08.239948+06:30	t	\N	Ingredients: lemon\n\nEffectiveness: release the tension
\.


--
-- Data for Name: order_items; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.order_items (id, order_id, batch_pk, qty_kg, unit_price, line_total) FROM stdin;
50	48	7	0.50	45.00	22.50
51	49	7	0.50	45.00	22.50
52	50	7	0.50	45.00	22.50
53	51	7	0.50	45.00	22.50
54	52	7	0.50	45.00	22.50
55	53	7	0.50	45.00	22.50
56	54	7	0.50	45.00	22.50
57	55	7	0.50	45.00	22.50
58	56	7	0.50	45.00	22.50
59	57	7	0.50	45.00	22.50
60	58	7	0.50	45.00	22.50
61	59	7	0.50	45.00	22.50
62	60	7	0.50	45.00	22.50
63	61	7	0.50	45.00	22.50
64	62	7	0.50	45.00	22.50
65	63	9	1.00	35.00	35.00
66	64	9	1.00	35.00	35.00
67	65	9	1.00	35.00	35.00
\.


--
-- Data for Name: order_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.order_messages (id, order_id, sender_id, sender_role, message, created_at) FROM stdin;
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.orders (id, customer_id, assigned_warehouse_id, status, delivery_address, preferred_date, subtotal, discount_amount, total_price, promotion_id, created_at, updated_at, pincode, delivery_charge, delivered_at, fulfillment, payment_method, payment_status, payment_reference, payment_phone, customer_seq) FROM stdin;
49	3	1	cancelled	142 Bargayar Rd, Sanchaung, Yangon	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:55.8991+06:30	2026-06-04 14:49:17.821959+06:30	11111	0.00	\N	pickup	\N	unpaid	\N	\N	2
48	3	1	cancelled	No. 23, Anawrahta Rd, Latha Township, Yangon	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:55.850501+06:30	2026-06-04 15:07:31.76751+06:30	11131	0.00	\N	pickup	\N	unpaid	\N	\N	1
52	3	1	cancelled	9 Thitsar Rd, South Okkalapa, Yangon	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.032784+06:30	2026-06-04 15:14:27.026982+06:30	11091	0.00	\N	pickup	\N	unpaid	\N	\N	5
57	3	1	cancelled	78 78th St, Chanmyathazi, Mandalay	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.247153+06:30	2026-06-04 15:22:59.311136+06:30	05021	0.00	\N	pickup	\N	unpaid	\N	\N	10
55	3	1	cancelled	64 Insein Rd, Kamayut, Yangon	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.180352+06:30	2026-06-04 15:23:07.691008+06:30	11041	0.00	\N	pickup	\N	unpaid	\N	\N	8
54	3	1	cancelled	31 University Ave, Bahan, Yangon	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.128318+06:30	2026-06-04 15:29:54.391267+06:30	11201	0.00	\N	pickup	\N	unpaid	\N	\N	7
51	3	1	cancelled	17 Strand Rd, Kyauktada, Yangon	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:55.990833+06:30	2026-06-04 15:30:03.591371+06:30	11182	0.00	\N	pickup	\N	unpaid	\N	\N	4
53	3	1	cancelled	256 Mahabandoola Rd, Pabedan, Yangon	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.070097+06:30	2026-06-04 15:30:28.08982+06:30	11141	0.00	\N	pickup	\N	unpaid	\N	\N	6
50	3	1	cancelled	88 Pyay Rd, Hlaing Township, Yangon	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:55.933682+06:30	2026-06-04 15:34:50.601299+06:30	11051	0.00	\N	pickup	\N	unpaid	\N	\N	3
63	3	1	cancelled	Test addr	\N	35.00	0.00	35.00	\N	2026-06-04 15:52:39.077517+06:30	2026-06-04 15:52:39.180193+06:30	\N	2.00	\N	delivery	cod	unpaid	\N	\N	16
56	3	1	shipped	12 Bogyoke Aung San Rd, Mandalay	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.20636+06:30	2026-06-04 15:52:39.197678+06:30	05011	0.00	\N	pickup	\N	unpaid	\N	\N	1
58	3	1	shipped	5 Zay Cho St, Maha Aungmye, Mandalay	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.271229+06:30	2026-06-04 15:52:39.197688+06:30	05031	0.00	\N	pickup	\N	unpaid	\N	\N	2
59	3	1	shipped	210 Pyin Oo Lwin Rd, Aungmyethazan, Mandalay	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.301529+06:30	2026-06-04 15:52:39.197693+06:30	05041	0.00	\N	pickup	\N	unpaid	\N	\N	3
60	3	1	shipped	3 Yaza Thingaha Rd, Ottarathiri, Naypyitaw	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.336513+06:30	2026-06-04 15:52:39.197698+06:30	15011	0.00	\N	pickup	\N	unpaid	\N	\N	4
62	3	1	shipped	19 Kanbawza Rd, Taunggyi, Shan State	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.388521+06:30	2026-06-05 08:51:58.429918+06:30	06011	0.00	\N	pickup	kpay	paid	KPAY649508522	+9599746916	6
64	3	1	assigned	Ohn Pin Village	2026-06-11	35.00	0.00	35.00	\N	2026-06-05 08:47:47.785398+06:30	2026-06-06 17:38:52.428492+06:30	Magway	2.00	\N	delivery	kpay	paid	KPAY649279159	+9599746916	7
65	3	1	shipped	Ohn Pin Village	2026-06-11	35.00	0.00	35.00	\N	2026-06-05 09:04:03.52633+06:30	2026-06-06 17:43:24.99841+06:30	Myanmar	2.00	\N	delivery	wavepay	paid	WAVE650254747	+9599746916	8
61	3	1	shipped	47 Thapyay Gone, Zabuthiri, Naypyitaw	\N	22.50	0.00	22.50	\N	2026-06-04 08:39:56.365965+06:30	2026-06-06 19:24:09.400169+06:30	15021	0.00	\N	pickup	kpay	paid	KPAY773842538	+95987654321	5
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payments (id, warehouse_id, subscription_id, plan_id, amount, method, payer, reference, status, created_at) FROM stdin;
18	1	21	1	599.00	kpay	Payment · +95974691655	KPAY546614342	paid	2026-06-04 04:16:54.732349+06:30
19	1	22	1	599.00	kpay	Test	WH1	paid	2026-06-04 08:33:26.901845+06:30
20	1	23	3	2499.00	kpay	Payment · +95974691655	KPAY645383125	paid	2026-06-05 07:43:04.176807+06:30
21	1	24	1	599.00	kpay	Transfer · +95974691655	KPAY650060647	paid	2026-06-05 09:01:01.619673+06:30
23	1	25	1	599.00	kpay	Transfer · +95974691655	KPAY770140043	paid	2026-06-06 18:22:21.100735+06:30
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
4	1	2	Black Jaggery	A	50.00	2026-06-06	35.00	rejected	Thanks for submitting Black Jaggery. We cannot approve it yet: the price per kg looks higher than similar listings, the uploaded image is a bit blurry, and we need a clearer description of the ingredients and health benefits. Please re-submit with an updated photo, a competitive price, and a fuller description, and we will review it again within 2 business days.	\N	\N	2026-06-04 04:27:08.568059+06:30	\N	\N	great packaging
3	1	2	Suagar Jaggery	A	50.00	2026-06-05	35.00	rejected	Thank you for submitting Sugar Jaggery for review. After a careful look by our product team, we are unable to approve this listing in its current form for several reasons. First, the price you set is noticeably higher than comparable jaggery products already on the platform, and we want pricing to stay fair and competitive for customers. Second, the product photo you uploaded is low resolution and slightly out of focus, which makes it hard for buyers to judge quality; please upload a clear, well-lit image on a plain background. Third, the ingredients section is incomplete and the effectiveness section does not explain the health benefits or recommended usage, so customers would not have enough information to make a confident purchase. Finally, please confirm the harvest/production date, since the value provided appears to be inconsistent with the stock you listed. Once you have updated the price, replaced the image, expanded both the ingredients and effectiveness descriptions, and verified the production date, please re-submit the request. Our team will then re-review it, usually within two business days, and notify you of the outcome. Thank you for your patience and for selling on our platform.	\N	\N	2026-06-04 04:22:18.641138+06:30	\N	\N	suagar, jaggery and good for stomach
6	1	2	Suagar Jaggery	A	50.00	2026-06-06	35.00	pending	\N	\N	\N	2026-06-05 07:12:17.569892+06:30	\N	req_07d58e69ab.jpg	Ingredients: sugar\n\nEffectiveness: release the tension
5	1	2	SuagarA Jaggery	A	50.00	2026-06-05	35.00	rejected	\N	1	\N	2026-06-04 09:06:08.647818+06:30	2026-06-05 07:24:00.695247+06:30	\N	Ingredients: sugar\n\nEffectiveness: release the tension
8	1	2	Suagar Jaggery	A	50.00	2026-06-06	35.00	approved	\N	1	10	2026-06-05 09:01:51.635675+06:30	2026-06-05 09:02:32.513776+06:30	\N	Ingredients: sugar\n\nEffectiveness: release the tension
9	1	2	TEST-CAT-10	B	25.00	2026-05-01	42.00	approved	\N	1	\N	2026-06-05 10:00:54.467566+06:30	2026-06-05 10:03:10.674484+06:30	\N	approval-flow test category
7	1	2	Suagar Jaggery	A	50.00	2026-06-04	35.00	rejected	\N	1	\N	2026-06-05 07:40:57.430974+06:30	2026-06-06 16:11:42.96459+06:30	\N	Ingredients: sugar\n\nEffectiveness: release the tension
11	1	2	Suagar Jaggery7	A	50.00	2026-06-08	35.00	pending	\N	\N	\N	2026-06-06 18:22:02.409286+06:30	\N	\N	Ingredients: lemon\n\nEffectiveness: release the tension
\.


--
-- Data for Name: promotions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.promotions (id, title, discount_percent, min_qty, start_date, end_date, is_active, created_at) FROM stdin;
1	10% off on 5kg+	15.00	5.00	2026-05-28	2026-07-02	t	2026-06-02 08:24:24.754347+06:30
2	Lucky Draw	20.00	20.00	2026-06-03	2026-07-03	t	2026-06-02 19:17:36.640339+06:30
6	Work Day	16.00	56.00	2026-06-05	2026-06-12	t	2026-06-04 14:12:47.372654+06:30
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

COPY public.users (id, name, email, password_hash, role, warehouse_id, created_at, phone, address, pincode, payment_pin_hash, pin_reset_code, pin_reset_expires, avatar_path, order_count, pay_otp_hash, pay_otp_expires) FROM stdin;
2	Warehouse Staff	staff@jaggery.local	$2b$12$p61.gYkioqHnJH.ky8k2qOQZGmR4/SPDd7TAvuuRiAPZdmv4PHz..	warehouse_staff	1	2026-06-02 08:24:24.761394+06:30	+95788888888	Ohn Pin Village	Yangon	$2b$12$jqg2EHrxVfp9Nc/o2AjlDuK565EoERUORIgyF3eSj05ZBYnu1rQkS	\N	\N	\N	0	\N	\N
3	Mg Mg	customer@jaggery.local	$2b$12$mzjs9uO.TB/Lu7ViMP72uO0QdjH/uWdtUrV22t8yw4irt7qlmhD/C	customer	\N	2026-06-02 08:24:24.761398+06:30	+95999999999	Ohn Pin Village	Myanmar	$2b$12$DARw76JyHrh6CImWYws.KemQAjidzDc/PO1smX9fjjmsdCug3e672	\N	\N	avatar_3_63248e97.jpg	8	\N	\N
1	Site Admin	admin@jaggery.local	$2b$12$PM.hnxfD4y1pn0ZSV4gjDOpSsG6qRlxPB.a7LrN2rE29vNJjg6lo2	admin	\N	2026-06-02 08:24:24.016597+06:30	\N	\N	\N	\N	\N	\N	\N	0	\N	\N
4	Aung Aung	aungaung@gmail.com	$2b$12$2tosiHjCdoKUxezjKQT7i.QiipRMs6UJRU/ozQ3edkYZJqJMalcTu	customer	\N	2026-06-02 20:05:37.774931+06:30	\N	\N	\N	\N	\N	\N	\N	0	\N	\N
\.


--
-- Data for Name: warehouse_subscriptions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.warehouse_subscriptions (id, warehouse_id, plan_id, start_date, end_date, price_paid, status, created_at) FROM stdin;
21	1	1	2026-06-04	2026-07-04	599.00	active	2026-06-04 04:16:54.729116+06:30
22	1	1	2026-06-04	2026-08-04	599.00	active	2026-06-04 08:33:26.8977+06:30
23	1	3	2026-06-05	2027-02-04	2499.00	active	2026-06-05 07:43:04.155701+06:30
24	1	1	2026-06-05	2027-03-04	599.00	active	2026-06-05 09:01:01.611169+06:30
25	1	1	2026-06-07	2027-04-04	599.00	active	2026-06-06 18:22:21.079258+06:30
\.


--
-- Data for Name: warehouses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.warehouses (id, name, location, phone, created_at, pincode, manager_name, email) FROM stdin;
1	Kolhapur Central	Kolhapur, MH	020-111-2222	2026-06-02 08:24:24.012998+06:30	\N	\N	\N
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

SELECT pg_catalog.setval('public.abandoned_carts_id_seq', 2, true);


--
-- Name: announcements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.announcements_id_seq', 6, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 703, true);


--
-- Name: delivery_charges_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.delivery_charges_id_seq', 4, true);


--
-- Name: jaggery_batches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.jaggery_batches_id_seq', 34, true);


--
-- Name: order_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.order_items_id_seq', 67, true);


--
-- Name: order_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.order_messages_id_seq', 3, true);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.orders_id_seq', 65, true);


--
-- Name: payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payments_id_seq', 23, true);


--
-- Name: price_alerts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.price_alerts_id_seq', 4, true);


--
-- Name: product_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.product_requests_id_seq', 11, true);


--
-- Name: promotions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.promotions_id_seq', 6, true);


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

SELECT pg_catalog.setval('public.subscription_plans_id_seq', 6, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 6, true);


--
-- Name: warehouse_subscriptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.warehouse_subscriptions_id_seq', 25, true);


--
-- Name: warehouses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.warehouses_id_seq', 5, true);


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

\unrestrict m2cjONJ0z16GNIkaAbudmuXZVvSTaKBkH3Gl9ZZyyXGSpnvVb5CTcD4NqX8LP6h

