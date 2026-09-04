--
-- PostgreSQL database dump
--

\restrict A5fhJgYgJ2fwjwv5YhYH3yCCrITAmYrjSuh7oTbD8NCXRbkambiWKeFEaC1SLcL

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
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
-- Name: customers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customers (
    customer_id character varying(50) NOT NULL,
    contact_consent boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: decision_action_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.decision_action_scores (
    decision_id character varying(50) NOT NULL,
    action_type character varying(50) NOT NULL,
    is_eligible boolean DEFAULT true NOT NULL,
    ineligible_reason text,
    predicted_success_probability double precision,
    uplift double precision,
    expected_incremental_utility_minor bigint,
    payment_processing_cost_minor bigint,
    action_cost_minor bigint,
    discount_cost_minor bigint,
    expected_merchant_value_minor bigint
);


--
-- Name: orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orders (
    order_id character varying(50) NOT NULL,
    customer_id character varying(50) NOT NULL,
    amount_minor bigint NOT NULL,
    currency character varying(3) DEFAULT 'INR'::character varying NOT NULL,
    status character varying(30) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: payment_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_events (
    event_id bigint NOT NULL,
    payment_id character varying(50) NOT NULL,
    provider_event_id character varying(100),
    event_type character varying(50) NOT NULL,
    event_time timestamp with time zone NOT NULL,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    raw_payload jsonb
);


--
-- Name: payment_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payment_events_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payment_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payment_events_event_id_seq OWNED BY public.payment_events.event_id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    payment_id character varying(50) NOT NULL,
    order_id character varying(50) NOT NULL,
    method character varying(30) NOT NULL,
    status character varying(30) NOT NULL,
    failure_reason character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: recovery_actions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recovery_actions (
    action_id character varying(50) NOT NULL,
    decision_id character varying(50) NOT NULL,
    action_type character varying(50) NOT NULL,
    execution_status character varying(30) NOT NULL,
    blocked_reason text,
    policy_checks jsonb,
    executed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: recovery_cases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recovery_cases (
    recovery_case_id character varying(50) NOT NULL,
    order_id character varying(50) NOT NULL,
    status character varying(30) NOT NULL,
    closure_reason character varying(50),
    opened_at timestamp with time zone DEFAULT now() NOT NULL,
    closed_at timestamp with time zone
);


--
-- Name: recovery_decisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recovery_decisions (
    decision_id character varying(50) NOT NULL,
    recovery_case_id character varying(50) NOT NULL,
    prediction_time timestamp with time zone DEFAULT now() NOT NULL,
    model_version character varying(100),
    proposed_action character varying(50) NOT NULL,
    feature_snapshot jsonb,
    explanation text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: recovery_outcomes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recovery_outcomes (
    outcome_id character varying(50) NOT NULL,
    recovery_case_id character varying(50) NOT NULL,
    action_id character varying(50),
    payment_id character varying(50),
    outcome_type character varying(50) NOT NULL,
    recovered_amount_minor bigint,
    outcome_time timestamp with time zone NOT NULL,
    time_to_recovery_seconds integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: payment_events event_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_events ALTER COLUMN event_id SET DEFAULT nextval('public.payment_events_event_id_seq'::regclass);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (customer_id);


--
-- Name: decision_action_scores decision_action_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decision_action_scores
    ADD CONSTRAINT decision_action_scores_pkey PRIMARY KEY (decision_id, action_type);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (order_id);


--
-- Name: payment_events payment_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_events
    ADD CONSTRAINT payment_events_pkey PRIMARY KEY (event_id);


--
-- Name: payment_events payment_events_provider_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_events
    ADD CONSTRAINT payment_events_provider_event_id_key UNIQUE (provider_event_id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (payment_id);


--
-- Name: recovery_actions recovery_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recovery_actions
    ADD CONSTRAINT recovery_actions_pkey PRIMARY KEY (action_id);


--
-- Name: recovery_cases recovery_cases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recovery_cases
    ADD CONSTRAINT recovery_cases_pkey PRIMARY KEY (recovery_case_id);


--
-- Name: recovery_decisions recovery_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recovery_decisions
    ADD CONSTRAINT recovery_decisions_pkey PRIMARY KEY (decision_id);


--
-- Name: recovery_outcomes recovery_outcomes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recovery_outcomes
    ADD CONSTRAINT recovery_outcomes_pkey PRIMARY KEY (outcome_id);


--
-- Name: uq_one_active_recovery_case_per_order; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_one_active_recovery_case_per_order ON public.recovery_cases USING btree (order_id) WHERE (closed_at IS NULL);


--
-- Name: decision_action_scores decision_action_scores_decision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decision_action_scores
    ADD CONSTRAINT decision_action_scores_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES public.recovery_decisions(decision_id);


--
-- Name: orders orders_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(customer_id);


--
-- Name: payment_events payment_events_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_events
    ADD CONSTRAINT payment_events_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(payment_id);


--
-- Name: payments payments_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(order_id);


--
-- Name: recovery_actions recovery_actions_decision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recovery_actions
    ADD CONSTRAINT recovery_actions_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES public.recovery_decisions(decision_id);


--
-- Name: recovery_cases recovery_cases_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recovery_cases
    ADD CONSTRAINT recovery_cases_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(order_id);


--
-- Name: recovery_decisions recovery_decisions_recovery_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recovery_decisions
    ADD CONSTRAINT recovery_decisions_recovery_case_id_fkey FOREIGN KEY (recovery_case_id) REFERENCES public.recovery_cases(recovery_case_id);


--
-- Name: recovery_outcomes recovery_outcomes_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recovery_outcomes
    ADD CONSTRAINT recovery_outcomes_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.recovery_actions(action_id);


--
-- Name: recovery_outcomes recovery_outcomes_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recovery_outcomes
    ADD CONSTRAINT recovery_outcomes_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(payment_id);


--
-- Name: recovery_outcomes recovery_outcomes_recovery_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recovery_outcomes
    ADD CONSTRAINT recovery_outcomes_recovery_case_id_fkey FOREIGN KEY (recovery_case_id) REFERENCES public.recovery_cases(recovery_case_id);


--
-- PostgreSQL database dump complete
--

\unrestrict A5fhJgYgJ2fwjwv5YhYH3yCCrITAmYrjSuh7oTbD8NCXRbkambiWKeFEaC1SLcL

