from preference_expander import PreferenceExpander


expander = PreferenceExpander()


expanded_preferences = expander.expand_preferences(["DSA"])
concepts = expanded_preferences["DSA"]


print("\nORIGINAL PREFERENCE:")

print("DSA")


print("\nEXPANDED CONCEPTS:")


for index, concept in enumerate(concepts, start=1):

    print(
        f"{index}. {concept}"
    )
