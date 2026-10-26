
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Workora Business Intelligence",
    page_icon="📊",
    layout="wide"
)

# --------------------------------------------------
# CONFIGURATION AND DATA LOADING
# --------------------------------------------------

from pathlib import Path

BASE = Path(__file__).resolve().parent

DATA_DIRS = [
    BASE,
    BASE / "data_analytics_dashboard_bundle",
    BASE.parent / "data_analytics_dashboard_bundle",
]

FILES = {
    "Website Traffic": "web_traffic.csv",
    "Customer Retention": "customer_churn.csv",
    "Regional Market": "regional_market.csv",
    "Checkout A/B Test": "checkout_ab_test.csv",
}


def load_csv(filename):
    for folder in DATA_DIRS:
        path = folder / filename
        if path.exists():
            try:
                return pd.read_csv(path)
            except Exception as exc:
                st.error(f"Unable to read {filename}: {exc}")
                st.stop()

    return None


def find_column(df, possible_names):
    """Find a column using case-insensitive exact matching."""
    normalised = {
        str(col).lower().replace("_", "").replace(" ", ""): col
        for col in df.columns
    }

    for name in possible_names:
        key = name.lower().replace("_", "").replace(" ", "")
        if key in normalised:
            return normalised[key]

    return None


def parse_date(df):
    col = find_column(
        df,
        ["Date", "SessionDate", "CreatedAt", "Timestamp"]
    )

    if col:
        parsed = pd.to_datetime(df[col], errors="coerce")
        if parsed.notna().any():
            df[col] = parsed
            return col

    return None


def numeric_series(df, column):
    return pd.to_numeric(df[column], errors="coerce")


def money(value):
    if pd.isna(value):
        return "N/A"
    return f"₹{value:,.2f}"


traffic = load_csv(FILES["Website Traffic"])
raw_customers = load_csv(FILES["Customer Retention"])
regional = load_csv(FILES["Regional Market"])
checkout = load_csv(FILES["Checkout A/B Test"])

datasets = {
    "Website Traffic": traffic,
    "Customer Retention": raw_customers,
    "Regional Market": regional,
    "Checkout A/B Test": checkout,
}

missing_files = [
    name for name, df in datasets.items()
    if df is None
]

if missing_files:
    st.error(
        "Missing datasets: " + ", ".join(missing_files)
    )
    st.info(
        "Keep data_analytics_dashboard_bundle and "
        "workora-dashboard as sibling folders inside Dashboard."
    )
    st.stop()


# --------------------------------------------------
# CUSTOMER DATA CLEANING
# --------------------------------------------------

customers = raw_customers.drop_duplicates().copy()

duplicates_removed = (
    len(raw_customers) - len(customers)
)

missing_customer_cells = int(
    raw_customers.isna().sum().sum()
)


# --------------------------------------------------
# DASHBOARD HEADER AND NAVIGATION
# --------------------------------------------------

st.title("📊 Workora Business Intelligence Dashboard")

st.caption(
    "Interactive analytics project using synthetic data. "
    "These are NOT real Workora business results."
)

page = st.sidebar.radio(
    "Choose dashboard page",
    [
        "Executive Overview",
        "Website Traffic",
        "Customer Retention",
        "Regional Market",
        "Checkout A/B Test",
        "Data Quality & Notes",
    ]
)


# --------------------------------------------------
# EXECUTIVE OVERVIEW
# --------------------------------------------------

if page == "Executive Overview":

    st.header("Executive Overview")

    st.write(
        "Explore acquisition, customer retention, "
        "regional market demand and checkout performance."
    )

    session_col = find_column(
        traffic, ["SessionID"]
    )

    customer_id = find_column(
        customers, ["CustomerID"]
    )

    churn_col = find_column(
        customers,
        ["Churn", "Churned", "IsChurn", "Exited"]
    )

    revenue_col = find_column(
        regional,
        ["Revenue", "TotalRevenue", "Sales"]
    )

    ticket_col = find_column(
        regional,
        [
            "AverageTicketSize",
            "AvgTicketSize",
            "AverageOrderValue",
            "AOV"
        ]
    )

    active_col = find_column(
        customers,
        ["IsActive", "ActiveUser", "ActiveUsers", "Active"]
    )

    c1, c2, c3, c4 = st.columns(4)

    # Revenue is shown only when the dataset contains revenue.
    with c1:
        if revenue_col:
            revenue = numeric_series(
                regional, revenue_col
            ).sum()
            st.metric("Total Revenue", money(revenue))
        else:
            st.metric(
                "Total Revenue",
                "N/A",
                help="No revenue field identified in the regional dataset."
            )

    # Active customers/users
    with c2:
        if active_col:
            values = customers[active_col]

            if values.dtype == object:
                active_count = values.astype(str).str.lower().isin(
                    ["yes", "true", "1", "active"]
                ).sum()
            else:
                active_count = (
                    pd.to_numeric(values, errors="coerce") == 1
                ).sum()

            st.metric("Active Users", f"{active_count:,}")
        else:
            st.metric(
                "Active Users",
                "N/A",
                help="No recognized active-user field was found."
            )

    # Churn rate based on recognized churn labels
    with c3:
        if churn_col:
            flags = (
                customers[churn_col]
                .astype("string")
                .str.lower()
                .str.strip()
            )

            known = flags.isin(
                ["yes", "no", "true", "false", "1", "0", "churned"]
            )

            churned = flags.isin(
                ["yes", "true", "1", "churned"]
            )

            if known.any():
                rate = churned[known].mean() * 100
                st.metric("Churn Rate", f"{rate:.2f}%")
            else:
                st.metric("Churn Rate", "N/A")
        else:
            st.metric("Churn Rate", "N/A")

    # Average ticket size
    with c4:
        if ticket_col:
            values = numeric_series(
                regional, ticket_col
            ).dropna()

            st.metric(
                "Avg Ticket Size",
                money(values.mean()) if not values.empty else "N/A"
            )
        else:
            st.metric(
                "Avg Ticket Size",
                "N/A",
                help="No recognized ticket-size field was found."
            )

    st.subheader("Dataset Overview")

    summary = pd.DataFrame([
        {
            "Dataset": name,
            "Rows": len(df),
            "Columns": len(df.columns),
            "Missing Cells": int(df.isna().sum().sum()),
            "Duplicate Rows": int(df.duplicated().sum()),
        }
        for name, df in datasets.items()
    ])

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True
    )

    # Checkout conversion overview
    variant_col = find_column(
        checkout, ["Variant"]
    )

    converted_col = find_column(
        checkout, ["Converted"]
    )

    if variant_col and converted_col:

        exp = checkout.copy()

        exp["_converted"] = (
            exp[converted_col]
            .astype(str)
            .str.lower()
            .str.strip()
            .map({
                "1": 1,
                "true": 1,
                "yes": 1,
                "converted": 1,
                "0": 0,
                "false": 0,
                "no": 0,
                "not converted": 0,
            })
        )

        exp = exp.dropna(
            subset=[variant_col, "_converted"]
        )

        result = exp.groupby(
            variant_col
        ).agg(
            Visitors=("_converted", "size"),
            Conversions=("_converted", "sum"),
        ).reset_index()

        if not result.empty:
            result["Conversion Rate (%)"] = (
                result["Conversions"]
                / result["Visitors"] * 100
            )

            st.subheader("Checkout Conversion Comparison")

            st.plotly_chart(
                px.bar(
                    result,
                    x=variant_col,
                    y="Conversion Rate (%)",
                    text_auto=".2f",
                    title="Conversion Rate by Variant",
                ),
                use_container_width=True
            )


# --------------------------------------------------
# WEBSITE TRAFFIC
# --------------------------------------------------

elif page == "Website Traffic":

    st.header("Website Traffic & Engagement")

    df = traffic.copy()

    date_col = parse_date(df)

    # Date filter
    if date_col and df[date_col].notna().any():

        valid_dates = df[date_col].dropna()

        selected_dates = st.sidebar.date_input(
            "Date range",
            value=(
                valid_dates.min().date(),
                valid_dates.max().date()
            ),
            key="traffic_dates"
        )

        if (
            isinstance(selected_dates, (tuple, list))
            and len(selected_dates) == 2
        ):
            start, end = selected_dates

            df = df[
                df[date_col].notna()
                & (df[date_col].dt.date >= start)
                & (df[date_col].dt.date <= end)
            ]

    channel_col = find_column(
        df,
        ["Channel", "Source", "TrafficSource", "Medium"]
    )

    if channel_col:

        channels = sorted(
            df[channel_col].dropna().astype(str).unique()
        )

        selected_channels = st.sidebar.multiselect(
            "Traffic channel",
            channels,
            default=channels,
            key="traffic_channels"
        )

        df = df[
            df[channel_col].astype(str).isin(selected_channels)
        ]

    session_col = find_column(
        df, ["SessionID"]
    )

    user_col = find_column(
        df, ["UserID", "VisitorID"]
    )

    a, b, c = st.columns(3)

    a.metric(
        "Total Sessions",
        f"{df[session_col].nunique():,}"
        if session_col else f"{len(df):,}"
    )

    b.metric(
        "Unique Users",
        f"{df[user_col].nunique():,}"
        if user_col else "N/A"
    )

    c.metric(
        "Filtered Records",
        f"{len(df):,}"
    )

    if date_col and not df.empty:

        trend = (
            df.dropna(subset=[date_col])
            .assign(
                Day=lambda x: x[date_col].dt.date
            )
            .groupby("Day")
            .size()
            .reset_index(name="Sessions")
        )

        st.plotly_chart(
            px.line(
                trend,
                x="Day",
                y="Sessions",
                markers=True,
                title="Website Sessions Over Time"
            ),
            use_container_width=True
        )

    if channel_col:

        channel_data = (
            df[channel_col]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .rename_axis("Channel")
            .reset_index(name="Sessions")
        )

        st.plotly_chart(
            px.bar(
                channel_data,
                x="Channel",
                y="Sessions",
                title="Sessions by Traffic Channel"
            ),
            use_container_width=True
        )

    st.subheader("Traffic Data Preview")

    st.dataframe(
        df.head(100),
        use_container_width=True
    )


# --------------------------------------------------
# CUSTOMER RETENTION
# --------------------------------------------------

elif page == "Customer Retention":

    st.header("Customer Retention & Churn")

    st.caption(
        "Exact duplicate rows are removed from this view. "
        "Missing values are reported, not automatically imputed."
    )

    df = customers.copy()

    region_col = find_column(
        df, ["Region", "RegionName", "Market"]
    )

    segment_col = find_column(
        df,
        ["Category", "Segment", "Plan", "SubscriptionType"]
    )

    if region_col:

        options = sorted(
            df[region_col].dropna().astype(str).unique()
        )

        selected = st.sidebar.multiselect(
            "Customer region",
            options,
            default=options,
            key="customer_regions"
        )

        df = df[
            df[region_col].astype(str).isin(selected)
        ]

    if segment_col:

        options = sorted(
            df[segment_col].dropna().astype(str).unique()
        )

        selected = st.sidebar.multiselect(
            "Customer segment",
            options,
            default=options,
            key="customer_segments"
        )

        df = df[
            df[segment_col].astype(str).isin(selected)
        ]

    customer_id = find_column(
        df, ["CustomerID"]
    )

    churn_col = find_column(
        df,
        ["Churn", "Churned", "IsChurn", "Exited"]
    )

    a, b, c = st.columns(3)

    a.metric(
        "Customer Records",
        f"{len(df):,}"
    )

    b.metric(
        "Unique Customers",
        f"{df[customer_id].nunique():,}"
        if customer_id else "N/A"
    )

    if churn_col:

        flags = (
            df[churn_col]
            .astype("string")
            .str.lower()
            .str.strip()
        )

        known = flags.isin(
            ["yes", "no", "true", "false", "1", "0", "churned"]
        )

        churned = flags.isin(
            ["yes", "true", "1", "churned"]
        )

        if known.any():
            rate = churned[known].mean() * 100
            c.metric("Churn Rate", f"{rate:.2f}%")
        else:
            c.metric("Churn Rate", "N/A")

        status_counts = (
            df[churn_col]
            .fillna("Missing")
            .astype(str)
            .value_counts()
            .rename_axis("Churn Status")
            .reset_index(name="Customers")
        )

        st.plotly_chart(
            px.bar(
                status_counts,
                x="Churn Status",
                y="Customers",
                title="Customer Churn Status"
            ),
            use_container_width=True
        )

    else:
        c.metric("Churn Rate", "N/A")

    numeric_cols = df.select_dtypes(
        include="number"
    ).columns.tolist()

    if numeric_cols:

        selected_metric = st.selectbox(
            "Explore customer metric",
            numeric_cols
        )

        st.plotly_chart(
            px.histogram(
                df,
                x=selected_metric,
                title=f"Distribution of {selected_metric}"
            ),
            use_container_width=True
        )

    st.subheader("Customer Data Preview")

    st.dataframe(
        df.head(100),
        use_container_width=True
    )


# --------------------------------------------------
# REGIONAL MARKET & DEMAND
# --------------------------------------------------

elif page == "Regional Market":

    st.header("Regional Market & Demand")

    df = regional.copy()

    # These fields match the regional_market.csv screenshot.
    required_columns = [
        "RegionID",
        "City",
        "State",
        "Latitude",
        "Longitude",
        "MonthlySearchDemand",
        "ExistingCompetitors",
        "MedianAnnualIncomeINRINR",
        "LeadConversionRate",
        "EstimatedAcquisitionCostINR",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        st.warning(
            "Some expected regional columns were not found: "
            + ", ".join(missing_columns)
        )
        st.write("Available columns:", list(df.columns))

    if "State" in df.columns:

        states = sorted(
            df["State"].dropna().astype(str).unique()
        )

        selected_states = st.sidebar.multiselect(
            "Select State",
            states,
            default=states,
            key="regional_states"
        )

        df = df[
            df["State"].astype(str).isin(selected_states)
        ]

    segment_col = find_column(
        df,
        ["PopulationSegment", "Population_Segment"]
    )

    if segment_col:

        segments = sorted(
            df[segment_col].dropna().astype(str).unique()
        )

        selected_segments = st.sidebar.multiselect(
            "Population Segment",
            segments,
            default=segments,
            key="regional_segments"
        )

        df = df[
            df[segment_col].astype(str).isin(selected_segments)
        ]

    if df.empty:
        st.warning("No regional records match the selected filters.")

    else:

        c1, c2, c3, c4 = st.columns(4)

        region_id = find_column(
            df, ["RegionID"]
        )

        search_col = find_column(
            df, ["MonthlySearchDemand"]
        )

        competitors_col = find_column(
            df, ["ExistingCompetitors"]
        )

        conversion_col = find_column(
            df, ["LeadConversionRate"]
        )

        acquisition_col = find_column(
            df, ["EstimatedAcquisitionCostINR"]
        )

        c1.metric(
            "Regions Analyzed",
            f"{df[region_id].nunique():,}"
            if region_id else f"{len(df):,}"
        )

        if search_col:

            searches = numeric_series(
                df, search_col
            )

            c2.metric(
                "Total Monthly Searches",
                f"{searches.sum():,.0f}"
            )

        else:
            c2.metric("Total Monthly Searches", "N/A")

        if competitors_col:

            competitors = numeric_series(
                df, competitors_col
            )

            c3.metric(
                "Average Competitors",
                f"{competitors.mean():.1f}"
            )

        else:
            c3.metric("Average Competitors", "N/A")

        if conversion_col:

            conversion = numeric_series(
                df, conversion_col
            )

            # The sample values appear to be decimals,
            # such as 0.1116, representing 11.16%.
            conversion_mean = conversion.mean()

            if pd.notna(conversion_mean):
                if conversion_mean <= 1:
                    conversion_mean *= 100

                c4.metric(
                    "Average Lead Conversion",
                    f"{conversion_mean:.2f}%"
                )
            else:
                c4.metric("Average Lead Conversion", "N/A")

        else:
            c4.metric("Average Lead Conversion", "N/A")

        # City demand chart
        st.subheader("Monthly Search Demand by City")

        if "City" in df.columns and search_col:

            city_data = (
                df.assign(
                    _searches=numeric_series(df, search_col)
                )
                .groupby("City", as_index=False)["_searches"]
                .sum()
                .sort_values("_searches", ascending=False)
                .head(20)
            )

            city_data = city_data.rename(
                columns={"_searches": "Monthly Searches"}
            )

            st.plotly_chart(
                px.bar(
                    city_data,
                    x="City",
                    y="Monthly Searches",
                    title="Top 20 Cities by Monthly Search Demand",
                    hover_data=["Monthly Searches"]
                ),
                use_container_width=True
            )

        # Competition chart
        if "City" in df.columns and competitors_col:

            competition_data = df[
                ["City", competitors_col]
            ].copy()

            competition_data[competitors_col] = numeric_series(
                competition_data, competitors_col
            )

            competition_data = (
                competition_data.groupby(
                    "City", as_index=False
                )[competitors_col]
                .mean()
                .sort_values(
                    competitors_col, ascending=False
                )
                .head(20)
            )

            st.plotly_chart(
                px.bar(
                    competition_data,
                    x="City",
                    y=competitors_col,
                    title="Cities by Existing Competitors"
                ),
                use_container_width=True
            )

        # Acquisition cost chart
        if "City" in df.columns and acquisition_col:

            cost_data = df[
                ["City", acquisition_col]
            ].copy()

            cost_data[acquisition_col] = numeric_series(
                cost_data, acquisition_col
            )

            cost_data = cost_data.dropna(
                subset=[acquisition_col]
            ).sort_values(
                acquisition_col, ascending=False
            ).head(20)

            st.plotly_chart(
                px.bar(
                    cost_data,
                    x="City",
                    y=acquisition_col,
                    title="Estimated Acquisition Cost by City"
                ),
                use_container_width=True
            )

        # Geographic map
        st.subheader("Regional Opportunity Map")

        lat_col = find_column(
            df, ["Latitude"]
        )

        lon_col = find_column(
            df, ["Longitude"]
        )

        if lat_col and lon_col:

            map_df = df.copy()

            map_df[lat_col] = numeric_series(
                map_df, lat_col
            )

            map_df[lon_col] = numeric_series(
                map_df, lon_col
            )

            map_df = map_df.dropna(
                subset=[lat_col, lon_col]
            )

            map_args = {
                "data_frame": map_df,
                "lat": lat_col,
                "lon": lon_col,
                "hover_name": "City" if "City" in map_df.columns else None,
                "zoom": 3,
                "title": "Regional Locations",
                "map_style": "open-street-map",
            }

            if segment_col:
                map_args["color"] = segment_col

            if search_col:
                map_args["size"] = search_col

            st.plotly_chart(
                px.scatter_map(**map_args),
                use_container_width=True
            )

        st.subheader("Regional Market Data")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# --------------------------------------------------
# CHECKOUT A/B TEST
# --------------------------------------------------

elif page == "Checkout A/B Test":

    st.header("Checkout A/B Test Analysis")

    df = checkout.copy()

    variant_col = find_column(
        df, ["Variant"]
    )

    converted_col = find_column(
        df, ["Converted"]
    )

    visitor_col = find_column(
        df, ["VisitorID"]
    )

    if not variant_col or not converted_col:

        st.warning(
            "Could not find the Variant and Converted fields."
        )

        st.write("Available columns:", list(df.columns))

        st.dataframe(
            df.head(100),
            use_container_width=True
        )

    else:

        df["_converted"] = (
            df[converted_col]
            .astype(str)
            .str.lower()
            .str.strip()
            .map({
                "1": 1,
                "true": 1,
                "yes": 1,
                "converted": 1,
                "0": 0,
                "false": 0,
                "no": 0,
                "not converted": 0,
            })
        )

        df = df.dropna(
            subset=[variant_col, "_converted"]
        )

        if visitor_col:

            duplicate_visitors = int(
                df[visitor_col].duplicated().sum()
            )

            st.caption(
                f"Duplicate VisitorID records detected: "
                f"{duplicate_visitors}"
            )

        result = df.groupby(
            variant_col
        ).agg(
            Visitors=("_converted", "size"),
            Conversions=("_converted", "sum")
        ).reset_index()

        result["Conversion Rate (%)"] = (
            result["Conversions"]
            / result["Visitors"] * 100
        )

        st.subheader("Experiment Results")

        st.dataframe(
            result,
            use_container_width=True,
            hide_index=True
        )

        st.plotly_chart(
            px.bar(
                result,
                x=variant_col,
                y="Conversion Rate (%)",
                text_auto=".2f",
                title="Conversion Rate by Variant"
            ),
            use_container_width=True
        )

        if len(result) >= 2:

            difference = (
                result.iloc[1]["Conversion Rate (%)"]
                - result.iloc[0]["Conversion Rate (%)"]
            )

            st.metric(
                "Conversion Rate Difference",
                f"{difference:+.2f} percentage points"
            )

        st.caption(
            "This is a descriptive comparison. "
            "It does not establish statistical significance or causation."
        )


# --------------------------------------------------
# DATA QUALITY AND DOCUMENTATION
# --------------------------------------------------

elif page == "Data Quality & Notes":

    st.header("Data Quality & Documentation")

    rows = []

    for name, df in datasets.items():

        rows.append({
            "Dataset": name,
            "Raw Rows": len(df),
            "Columns": len(df.columns),
            "Exact Duplicate Rows": int(df.duplicated().sum()),
            "Missing Cells": int(df.isna().sum().sum()),
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Customer Data Cleaning")

    st.write(
        f"Raw customer rows: **{len(raw_customers):,}**"
    )

    st.write(
        f"Exact duplicate rows removed from retention analysis: "
        f"**{duplicates_removed:,}**"
    )

    st.write(
        f"Missing cells in raw customer dataset: "
        f"**{missing_customer_cells:,}**"
    )

    st.write(
        "Missing values are not automatically imputed. "
        "Potential outliers are retained until they are investigated "
        "and a justified exclusion rule is documented."
    )

    st.subheader("Expected Dataset Keys")

    st.write(
        "- Website traffic: SessionID is described as unique."
    )

    st.write(
        "- Customer retention: CustomerID is described as unique, "
        "but the raw data contains intentional quality issues."
    )

    st.write(
        "- Regional market: RegionID is described as unique."
    )

    st.write(
        "- Checkout experiment: VisitorID is described as unique."
    )

    st.subheader("Joins and Assumptions")

    st.write(
        "These datasets describe different entities: sessions, customers, "
        "regions and experiment visitors. They are analysed separately "
        "unless a valid shared key and relationship can be confirmed."
    )

    st.write(
        "Total revenue and average ticket size are not calculated from "
        "regional search demand or acquisition cost. They are shown only "
        "if a suitable field exists in the relevant dataset."
    )

    st.write(
        "Churn rate is calculated from records with recognized churn "
        "outcomes. Conversion rate uses recognized conversion outcomes."
    )

    st.subheader("Synthetic Data Notice")

    st.warning(
        "All records are synthetic and intended only for learning. "
        "Do not present these values as real Workora business results."
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Workora Dashboard Pack | Interactive Business Intelligence "
    "| Synthetic Data Only"
)
