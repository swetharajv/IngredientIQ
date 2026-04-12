st.title("🧴 IngredientIQ")
st.subheader("Cosmetic Ingredient Safety Checker")

mode = st.radio("Mode", ["Single ingredient", "Compare ingredients"])

if mode == "Single ingredient":
    ingredient = st.text_input("Enter ingredient name",
        placeholder="e.g. retinol, niacinamide")
    ingredients = [ingredient] if ingredient else []
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        i1 = st.text_input("Ingredient 1", placeholder="retinol")
    with col2:
        i2 = st.text_input("Ingredient 2", placeholder="niacinamide")
    with col3:
        i3 = st.text_input("Ingredient 3", placeholder="salicylic acid")
    ingredients = [i for i in [i1, i2, i3] if i]

for ingredient in ingredients:
    if ingredient:
        with st.spinner(f"Looking up {ingredient}..."):
            total = get_fda_total(ingredient)
            reactions = get_top_reactions(ingredient)
        
        if total == 0:
            st.warning(f"No data found for: {ingredient}")
        else:
            score, label = clean_beauty_score(total)
            st.markdown(f"### {ingredient.title()}")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Clean Beauty Score", f"{score}/10")
                st.write(label)
            with col2:
                st.metric("FDA Reports", f"{total:,}")
            
            if reactions:
                counts = Counter(reactions)
                top10 = counts.most_common(10)
                labels = [r[0] for r in top10]
                values = [r[1] for r in top10]
                fig = px.bar(x=values, y=labels, orientation="h",
                            title=f"Top Reactions for {ingredient.title()}",
                            color=values, color_continuous_scale="Reds")
                fig.update_layout(height=350, showlegend=False,
                                yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")

st.caption("Data: FDA FAERS via openFDA API. Built by Clinical Data Intelligence.")
