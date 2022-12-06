# Create List
rm(list = ls())

# Create list with 8760 entries. 8760 h = 1 year
basicConsumption = rep(5.53, 8760)

# Add noise
basicConsumption.rand <- c()
for(i in 1:8760){
  basicConsumption.rand <- append(basicConsumption.rand, rnorm(1, mean = basicConsumption[i], sd = 0.02))
}
#basicConsumption.rand = jitter(basicConsumption, factor=1, amount = NULL)

# Set negative values to 0
basicConsumption.rand[basicConsumption.rand<0] <- 0

# round basicConsumption.rand to 2 digits
basicConsumption.rounded = round(basicConsumption.rand, digits = 4)


# Creating dateTime list
start <- as.POSIXct("2022-01-01")
interval <- 60
end <- start + as.difftime(365, units="days")
dateTime = seq(from=start, by=interval*60, to=end - 1)

# Add dateTime list to Output
output <- as.data.frame(dateTime)

# Adding date.hour to Output
output["basicConsumption (kWh)"] <- as.data.frame(basicConsumption.rounded)

# Write Output to CSV
output
write.csv(output,"basicCounsumption_dummyData.csv", row.names = FALSE)
#write.csv(output,"basicConsumption_dummyData.csv", row.names = FALSE)