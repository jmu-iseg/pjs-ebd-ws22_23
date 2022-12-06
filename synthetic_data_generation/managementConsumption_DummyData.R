# Create List
rm(list = ls())

# Define avg daily kWh consumption per month
data.month <- c(111, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111)

# Define Days per Month
days.per.month <- c(31,28,31,30,31,30,31,31,30,31,30,31)

# Append Days to Month
data.day <- c()
for(i in 1:11){
  data.day <- append(data.day, seq(from = data.month[i], to = data.month[i+1],
                                   length = days.per.month[i]))
}
data.day <- append(data.day, seq(from = data.month[12], to = data.month[1],
                                 length = days.per.month[12]))

# Create Daily Hours Sequence
hour.ind <- seq(from = 1, to = 24, length = 24)

# normally distributed daily consumption: Peak at 10:00 and 14:00, Low at 12:00
# first peak
data.hour1.dnorm <- dnorm(hour.ind, mean = 10, sd = 1.7)
data.hour1.dnorm.corr <- data.hour1.dnorm*5.7
data.hour1.dnorm.corr.sum <- sum(data.hour1.dnorm.corr)
data.hour1.dnorm.corr.perc <- data.hour1.dnorm.corr/data.hour1.dnorm.corr.sum

# first peak
data.hour2.dnorm <- dnorm(hour.ind, mean = 14, sd = 1.7)
data.hour2.dnorm.corr <- data.hour2.dnorm*5.7
data.hour2.dnorm.corr.sum <- sum(data.hour2.dnorm.corr)
data.hour2.dnorm.corr.perc <- data.hour2.dnorm.corr/data.hour2.dnorm.corr.sum

# Appened distribution to Date.Hour list for peak 1 and 2
data.hour1 <- c()
for(i in 1:365){
    data.hour1 <- append(data.hour1, data.day[i]*data.hour1.dnorm.corr.perc)
}
data.hour2 <- c()
for(i in 1:365){
  data.hour2 <- append(data.hour2, data.day[i]*data.hour2.dnorm.corr.perc)
}

# Merge peak1 and peak2 into one dataSet
data.hour.total = (data.hour1 + data.hour2) * 0.5

# Randomize data
data.hour.total.rand <- c()
for(i in 1:8760){
  data.hour.total.rand <- append(data.hour.total.rand, rnorm(1, mean = data.hour.total[i], sd = 0.5))
}


# Set negative values to 0
data.hour.total.rand[data.hour.total.rand<0] <- 0

# set consumption = 0 on weekends. 01.01.2022 = saturday
# 1 to 48 = 0, 49 to 168 = original values
listLength = length(data.hour.total.rand)

dateTimeCount = 1
weekCount = 1
while (weekCount <= 52) {
  nHourPerWeek = 1
  while (nHourPerWeek <= 48) { # is it a saturday or sunday?
    data.hour.total.rand[dateTimeCount] = 0 # set consumption = 0
    nHourPerWeek = nHourPerWeek+1
    dateTimeCount = dateTimeCount+1
  }
  while (nHourPerWeek <= 168) {
    nHourPerWeek = nHourPerWeek+1
    dateTimeCount = dateTimeCount+1
  }
  weekCount = weekCount+1
}

# Plotting  
par(mfrow = c(1,1))
plot(data.hour.total[1:240], type = "l", main = "January")

# Plotting
summary(data.hour.total.rand)
par(mfrow = c(1,1))
plot(data.hour.total.rand[1:160], type = "l")

# round data.hour.rand to 2 digits
managementConsumption = round(data.hour.total.rand, digits = 4)


# Creating dateTime list
start <- as.POSIXct("2022-01-01")
interval <- 60
end <- start + as.difftime(365, units="days")
dateTime = seq(from=start, by=interval*60, to=end - 1)

# Add dateTime list to Output
output <- as.data.frame(dateTime)

# Adding date.hour to Output
output["managementConsumption (kWh)"] <- as.data.frame(managementConsumption)

# Write Output to CSV
output
write.csv(output,"managementConsumption_dummyData.csv", row.names = FALSE)